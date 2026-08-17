from __future__ import annotations

import asyncio

import httpx
import structlog
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_common.messaging.rabbitmq import (
    consume_json,
    declare_dlq,
    declare_queue,
    rabbit_connection,
)
from studio_common.orchestration.orchestrator_flags import (
    PAUSE_IMPORT_KEY,
    redis_url_from_env,
    wait_while_orchestrator_paused,
)
from studio_integration_sdk.registry import AdapterModule

from app.config import IntegrationsSettings
from app.domain.worker_handle import handle_import_payload
from app.worker_sweep import start_import_sweeper

log = structlog.get_logger("integrations.worker")

__all__ = [
    "start_import_sweeper",
    "start_import_worker",
]


def start_import_worker(
    settings: IntegrationsSettings,
    session_factory: async_sessionmaker[AsyncSession],
    http_client: httpx.AsyncClient,
    adapters: dict[str, AdapterModule],
) -> asyncio.Task[None] | None:
    if not settings.rabbitmq_url:
        log.warning("rabbitmq_disabled")
        return None

    async def _runner() -> None:
        async with rabbit_connection(settings.rabbitmq_url) as connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=3)
            queue = await declare_queue(channel, settings.import_queue)
            dlq = await declare_dlq(channel, settings.import_queue)
            await declare_queue(channel, settings.search_index_queue)

            async def handle(payload: dict[str, object], _message: AbstractIncomingMessage) -> None:
                redis_url = redis_url_from_env()
                await wait_while_orchestrator_paused(redis_url, PAUSE_IMPORT_KEY)
                await handle_import_payload(
                    payload,
                    channel=channel,
                    session_factory=session_factory,
                    http_client=http_client,
                    settings=settings,
                    adapters=adapters,
                )

            await consume_json(queue, handle, dlq=dlq)

    return asyncio.create_task(_runner())
