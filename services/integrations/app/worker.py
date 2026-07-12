from __future__ import annotations

import asyncio
import uuid

import httpx
import structlog
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_common.orchestrator_flags import (
    PAUSE_IMPORT_KEY,
    orchestrator_flag_enabled,
    redis_url_from_env,
)
from studio_common.rabbitmq import consume_json, declare_dlq, declare_queue, rabbit_connection
from studio_integration_sdk.registry import AdapterModule

from app.config import IntegrationsSettings
from app.domain.jobs import get_import_job, run_import_job
from app.domain.messaging import publish_pack_index

log = structlog.get_logger("integrations.worker")


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
            await channel.set_qos(prefetch_count=1)
            queue = await declare_queue(channel, settings.import_queue)
            dlq = await declare_dlq(channel, settings.import_queue)
            await declare_queue(channel, settings.search_index_queue)

            async def handle(payload: dict[str, object], _message: AbstractIncomingMessage) -> None:
                redis_url = redis_url_from_env()
                while await orchestrator_flag_enabled(redis_url, PAUSE_IMPORT_KEY):
                    await asyncio.sleep(5)
                job_id = uuid.UUID(str(payload["job_id"]))
                user_id = uuid.UUID(str(payload["user_id"]))
                platform_id = str(payload["platform_id"])
                adapter = adapters.get(platform_id)
                if adapter is None:
                    msg = f"unknown platform {platform_id}"
                    raise ValueError(msg)

                async with session_factory() as session:
                    job = await get_import_job(session, user_id=user_id, job_id=job_id)
                    updated = await run_import_job(
                        session,
                        http_client,
                        settings,
                        adapter,
                        job,
                    )
                    if updated.pack_version_id is not None:
                        await publish_pack_index(
                            channel,
                            settings,
                            user_id=user_id,
                            pack_version_id=updated.pack_version_id,
                        )

            await consume_json(queue, handle, dlq=dlq)

    return asyncio.create_task(_runner())
