from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict

import httpx
import structlog
from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_common.rabbitmq import consume_json, declare_dlq, declare_queue, rabbit_connection
from studio_common.system_auth import system_token_headers

from app.config import LabRunnerSettings
from app.domain.runner import run_lab
from app.job_persist import mark_running, store_outcome

log = structlog.get_logger("lab_runner.worker")

_mark_running = mark_running
_store_outcome = store_outcome


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

    if not await mark_running(session_factory, lab_run_id, attempt_id, pack_root, step):
        return

    outcome = await asyncio.to_thread(run_lab, settings, pack_root=pack_root, step=step)
    await store_outcome(session_factory, lab_run_id, outcome)

    response = await http_client.post(
        f"{settings.grading_service_url}/internal/v1/grading/lab/complete",
        json={"attempt_id": str(attempt_id), **asdict(outcome)},
        headers=system_token_headers(),
        timeout=30,
    )
    response.raise_for_status()
    log.info(
        "lab_run_completed",
        lab_run_id=str(lab_run_id),
        attempt_id=str(attempt_id),
        passed=outcome.passed,
    )
