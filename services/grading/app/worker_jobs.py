from __future__ import annotations

import uuid

import httpx
import structlog
from aio_pika.abc import AbstractChannel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import GradingSettings
from app.domain.lab import get_lab_result
from app.domain.lab_jobs.worker import (
    complete_lab_when_pack_unavailable,
    fetch_pack_root,
    publish_lab_job,
)

log = structlog.get_logger("grading.worker")


async def process_grading_job(
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

    try:
        pack_root = await fetch_pack_root(
            http_client,
            settings,
            user_id=user_id,
            pack_version_id=pack_version_id,
        )
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        log.warning("lab_pack_root_failed", attempt_id=str(attempt_id), error=str(exc))
        async with session_factory() as session:
            await complete_lab_when_pack_unavailable(
                session,
                settings,
                http_client,
                attempt_id=attempt_id,
                user_id=user_id,
                step=step,
            )
        return

    await publish_lab_job(
        channel,
        settings,
        lab_run_id=uuid.uuid4(),
        attempt_id=attempt_id,
        pack_root=pack_root,
        step=step,
    )
    log.info("lab_job_published", attempt_id=str(attempt_id))
