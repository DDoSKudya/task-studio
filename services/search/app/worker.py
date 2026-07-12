from __future__ import annotations

import asyncio
import uuid

import httpx
import structlog
from aio_pika.abc import AbstractIncomingMessage
from meilisearch.client import Client
from studio_common.orchestrator_flags import (
    PAUSE_SEARCH_INDEX_KEY,
    orchestrator_flag_enabled,
    redis_url_from_env,
)
from studio_common.rabbitmq import consume_json, declare_dlq, declare_queue, rabbit_connection

from app.config import SearchSettings
from app.domain.indexing import index_external_course, index_pack_version

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
                while await orchestrator_flag_enabled(redis_url, PAUSE_SEARCH_INDEX_KEY):
                    await asyncio.sleep(5)
                op = str(payload.get("op", "upsert"))
                user_id = uuid.UUID(str(payload["user_id"]))
                if op == "upsert_external":
                    await index_external_course(
                        meili,
                        settings,
                        user_id=user_id,
                        platform=str(payload["platform"]),
                        external_id=str(payload["external_id"]),
                        title=str(payload["title"]),
                        description=str(payload.get("description", "")),
                    )
                    return

                pack_version_id = uuid.UUID(str(payload["pack_version_id"]))
                rank_raw = payload.get("rank_tier", 1)
                rank_tier = int(rank_raw) if isinstance(rank_raw, int) else 1
                await index_pack_version(
                    meili,
                    http_client,
                    settings,
                    user_id=user_id,
                    pack_version_id=pack_version_id,
                    rank_tier=rank_tier,
                )

            await consume_json(queue, handle, dlq=dlq)

    return asyncio.create_task(_runner())
