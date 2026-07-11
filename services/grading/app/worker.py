from __future__ import annotations

import asyncio
import uuid

import httpx
import structlog
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage
from app.config import GradingSettings
from app.domain.lab import fetch_pack_root, get_lab_result, publish_lab_job
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_common.rabbitmq import consume_json, declare_dlq, declare_queue, rabbit_connection

log = structlog.get_logger("grading.worker")


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
                await _process_job(settings, session_factory, http_client, channel, payload)

            await consume_json(queue, handle, dlq=dlq)

    return asyncio.create_task(_runner())


async def _process_job(
    settings: GradingSettings,
    session_factory: async_sessionmaker[AsyncSession],
    http_client: httpx.AsyncClient,
    channel: AbstractChannel,
    payload: dict[str, object],
) -> None:
    if payload.get("type") != "lab":
        return

    attempt_id = uuid.UUID(str(payload["attempt_id"]))
    user_id = uuid.UUID(str(payload["user_id"]))
    pack_version_id = uuid.UUID(str(payload["pack_version_id"]))
    step = payload.get("step")
    if not isinstance(step, dict):
        msg = "grading job requires step object"
        raise ValueError(msg)

    async with session_factory() as session:
        existing = await get_lab_result(session, attempt_id)
        if existing is not None and existing.details.get("status") == "completed":
            return

    pack_root = await fetch_pack_root(
        http_client,
        settings,
        user_id=user_id,
        pack_version_id=pack_version_id,
    )
    await publish_lab_job(
        channel,
        settings,
        lab_run_id=uuid.uuid4(),
        attempt_id=attempt_id,
        pack_root=pack_root,
        step=step,
    )
    log.info("lab_job_published", attempt_id=str(attempt_id))
