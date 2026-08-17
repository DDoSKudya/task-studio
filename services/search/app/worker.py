from __future__ import annotations

import asyncio

import httpx
import structlog
from aio_pika.abc import AbstractIncomingMessage
from meilisearch.client import Client
from studio_common.messaging.rabbitmq import (
    consume_json,
    declare_dlq,
    declare_queue,
    rabbit_connection,
)
from studio_common.orchestration.orchestrator_flags import (
    PAUSE_SEARCH_INDEX_KEY,
    redis_url_from_env,
    wait_while_orchestrator_paused,
)

from app.config import SearchSettings
from app.domain.worker_handle import handle_index_payload

log = structlog.get_logger("search.worker")


def start_index_worker(
    settings: SearchSettings,
    meili: Client,
    http_client: httpx.AsyncClient,
) -> asyncio.Task[None] | None:
    if not settings.rabbitmq_url:
        log.warning("rabbitmq_disabled")
        return None

    async def _runner() -> None:
        async with rabbit_connection(settings.rabbitmq_url) as connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=5)
            queue = await declare_queue(channel, settings.search_index_queue)
            dlq = await declare_dlq(channel, settings.search_index_queue)

            async def handle(payload: dict[str, object], _message: AbstractIncomingMessage) -> None:
                redis_url = redis_url_from_env()
                await wait_while_orchestrator_paused(redis_url, PAUSE_SEARCH_INDEX_KEY)
                await handle_index_payload(
                    payload,
                    meili=meili,
                    http_client=http_client,
                    settings=settings,
                )

            await consume_json(queue, handle, dlq=dlq)

    return asyncio.create_task(_runner())
