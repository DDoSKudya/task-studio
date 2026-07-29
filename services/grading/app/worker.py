from __future__ import annotations

import asyncio

import httpx
import structlog
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_common.rabbitmq import consume_json, declare_dlq, declare_queue, rabbit_connection

from app.config import GradingSettings
from app.worker_jobs import process_grading_job

log = structlog.get_logger("grading.worker")

_process_job = process_grading_job


def start_grading_worker(
    settings: GradingSettings,
    session_factory: async_sessionmaker[AsyncSession],
    http_client: httpx.AsyncClient,
) -> asyncio.Task[None] | None:
    if not settings.rabbitmq_url:
        log.warning("rabbitmq_disabled")
        return None

    async def _runner() -> None:
        async with rabbit_connection(settings.rabbitmq_url) as connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=5)
            queue = await declare_queue(channel, settings.grading_jobs_queue)
            dlq = await declare_dlq(channel, settings.grading_jobs_queue)

            async def handle(payload: dict[str, object], _message: AbstractIncomingMessage) -> None:
                await process_grading_job(settings, session_factory, http_client, channel, payload)

            await consume_json(queue, handle, dlq=dlq)

    return asyncio.create_task(_runner())
