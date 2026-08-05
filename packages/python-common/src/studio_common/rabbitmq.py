from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import aio_pika
from aio_pika.abc import (
    AbstractChannel,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)
from sqlalchemy.exc import SQLAlchemyError

_HANDLER_ERRORS = (
    TimeoutError,
    ConnectionError,
    OSError,
    SQLAlchemyError,
    ValueError,
    TypeError,
    KeyError,
    LookupError,
    RuntimeError,
)


@asynccontextmanager
async def rabbit_connection(url: str) -> AsyncIterator[AbstractRobustConnection]:
    connection = await aio_pika.connect_robust(url)
    try:
        yield connection
    finally:
        await connection.close()


async def declare_queue(channel: AbstractChannel, name: str) -> AbstractQueue:
    return await channel.declare_queue(name, durable=True)


async def declare_dlq(channel: AbstractChannel, queue_name: str) -> AbstractQueue:
    dlq_name = f"{queue_name}.dlq"
    return await channel.declare_queue(dlq_name, durable=True)


async def publish_json(
    channel: AbstractChannel,
    queue_name: str,
    payload: dict[str, object],
    *,
    message_id: str | None = None,
) -> None:
    body = json.dumps(payload).encode("utf-8")
    mid = message_id
    if not mid:
        raw_mid = payload.get("message_id")
        mid = str(raw_mid) if raw_mid else str(uuid.uuid4())
    await channel.default_exchange.publish(
        aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=mid,
        ),
        routing_key=queue_name,
    )


async def _forward_to_dlq(dlq: AbstractQueue, body: bytes) -> None:
    await dlq.channel.default_exchange.publish(
        aio_pika.Message(body=body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=dlq.name,
    )


def _classify_error(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError | ConnectionError | OSError):
        return "transient"
    return "permanent"


async def consume_json(
    queue: AbstractQueue,
    handler: Callable[[dict[str, object], AbstractIncomingMessage], Awaitable[None]],
    *,
    dlq: AbstractQueue | None = None,
) -> None:
    classify = os.getenv("RABBIT_CLASSIFY_ERRORS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process(requeue=False):
                try:
                    raw = json.loads(message.body.decode("utf-8"))
                except json.JSONDecodeError:
                    if dlq is not None:
                        await _forward_to_dlq(dlq, message.body)
                    continue
                if not isinstance(raw, dict):
                    if dlq is not None:
                        await _forward_to_dlq(dlq, message.body)
                    continue
                try:
                    await handler(raw, message)
                except asyncio.CancelledError:
                    raise
                except _HANDLER_ERRORS as exc:
                    if classify and _classify_error(exc) == "transient":
                        raise
                    if dlq is not None:
                        await _forward_to_dlq(dlq, message.body)
