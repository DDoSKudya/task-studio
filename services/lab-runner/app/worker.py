from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict
from datetime import UTC, datetime

import httpx
import structlog
from aio_pika.abc import AbstractIncomingMessage
from app.config import LabRunnerSettings
from app.domain.runner import LabRunOutcome, run_lab
from app.infra.models import LabRun
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_common.rabbitmq import consume_json, declare_dlq, declare_queue, rabbit_connection

log = structlog.get_logger("lab_runner.worker")


def start_lab_worker(
    settings: LabRunnerSettings,
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
            queue = await declare_queue(channel, settings.lab_jobs_queue)
            dlq = await declare_dlq(channel, settings.lab_jobs_queue)

            async def handle(payload: dict[str, object], _message: AbstractIncomingMessage) -> None:
                await _process_job(settings, session_factory, http_client, payload)

            await consume_json(queue, handle, dlq=dlq)

    return asyncio.create_task(_runner())


async def _process_job(
    settings: LabRunnerSettings,
    session_factory: async_sessionmaker[AsyncSession],
    http_client: httpx.AsyncClient,
    payload: dict[str, object],
) -> None:
    lab_run_id = uuid.UUID(str(payload["lab_run_id"]))
    attempt_id = uuid.UUID(str(payload["attempt_id"]))
    pack_root = str(payload["pack_root"])
    step = payload.get("step")
    if not isinstance(step, dict):
        msg = "lab job requires step object"
        raise ValueError(msg)

    if not await _mark_running(session_factory, lab_run_id, attempt_id, pack_root, step):
        return

    outcome = await asyncio.to_thread(run_lab, settings, pack_root=pack_root, step=step)
    await _store_outcome(session_factory, lab_run_id, outcome)

    response = await http_client.post(
        f"{settings.grading_service_url}/internal/v1/grading/lab/complete",
        json={"attempt_id": str(attempt_id), **asdict(outcome)},
        timeout=30,
    )
    response.raise_for_status()
    log.info("lab_run_completed", lab_run_id=str(lab_run_id), attempt_id=str(attempt_id), passed=outcome.passed)


async def _mark_running(
    session_factory: async_sessionmaker[AsyncSession],
    lab_run_id: uuid.UUID,
    attempt_id: uuid.UUID,
    pack_root: str,
    step: dict[str, object],
) -> bool:
    async with session_factory() as session:
        existing = await session.get(LabRun, lab_run_id)
        if existing is not None and existing.status == "completed":
            return False
        if existing is None:
            session.add(
                LabRun(
                    id=lab_run_id,
                    attempt_id=attempt_id,
                    status="running",
                    pack_root=pack_root,
                    step=step,
                )
            )
        else:
            existing.status = "running"
        await session.commit()
    return True


async def _store_outcome(
    session_factory: async_sessionmaker[AsyncSession],
    lab_run_id: uuid.UUID,
    outcome: LabRunOutcome,
) -> None:
    async with session_factory() as session:
        row = await session.get(LabRun, lab_run_id)
        if row is None:
            return
        row.status = "completed"
        row.finished_at = datetime.now(UTC)
        row.result = asdict(outcome)
        await session.commit()
