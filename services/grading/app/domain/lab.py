from __future__ import annotations

import uuid

import httpx
import structlog
from aio_pika.abc import AbstractChannel
from app.config import GradingSettings
from app.domain.check import GradingError
from app.infra.models import GradingResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_common.rabbitmq import declare_queue, publish_json, rabbit_connection
from studio_contracts.catalog_schemas import PackVersionContext
from studio_contracts.grading_schemas import GradingLabSubmitResponse

log = structlog.get_logger("grading.lab")


async def get_lab_result(session: AsyncSession, attempt_id: uuid.UUID) -> GradingResult | None:
    row = await session.execute(
        select(GradingResult).where(GradingResult.attempt_id == attempt_id)
    )
    return row.scalar_one_or_none()


async def enqueue_lab_job(
    session: AsyncSession,
    settings: GradingSettings,
    *,
    attempt_id: uuid.UUID,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
    step: dict[str, object],
) -> GradingLabSubmitResponse:
    if not settings.rabbitmq_url:
        raise GradingError(503, "grading queue unavailable")

    existing = await get_lab_result(session, attempt_id)
    if existing is not None and existing.details.get("status") == "completed":
        return GradingLabSubmitResponse(status="pending", attempt_id=str(attempt_id))

    if existing is None:
        session.add(
            GradingResult(
                attempt_id=attempt_id,
                checker="lab",
                passed=False,
                score=0.0,
                details={"status": "pending"},
                duration_ms=0,
            )
        )
        await session.commit()

    async with rabbit_connection(settings.rabbitmq_url) as connection:
        channel = await connection.channel()
        await declare_queue(channel, settings.grading_jobs_queue)
        await publish_json(
            channel,
            settings.grading_jobs_queue,
            {
                "attempt_id": str(attempt_id),
                "user_id": str(user_id),
                "pack_version_id": str(pack_version_id),
                "step": step,
                "type": "lab",
            },
        )

    log.info("lab_job_enqueued", attempt_id=str(attempt_id))
    return GradingLabSubmitResponse(status="pending", attempt_id=str(attempt_id))


async def complete_lab_job(
    session: AsyncSession,
    settings: GradingSettings,
    client: httpx.AsyncClient,
    *,
    attempt_id: uuid.UUID,
    passed: bool,
    score: float,
    feedback: str | None,
    details: dict[str, object],
    duration_ms: int,
) -> None:
    await _persist_lab_result(
        session,
        attempt_id,
        passed=passed,
        score=score,
        details=_result_details(details, feedback=feedback, status="completed"),
        duration_ms=duration_ms,
    )

    response = await client.post(
        f"{settings.sessions_service_url}/internal/v1/sessions/attempts/{attempt_id}/complete",
        json={
            "passed": passed,
            "score": score,
            "feedback": feedback,
            "details": details,
        },
        timeout=30,
    )
    response.raise_for_status()
    log.info("lab_job_completed", attempt_id=str(attempt_id), passed=passed)


async def fetch_pack_root(
    client: httpx.AsyncClient,
    settings: GradingSettings,
    *,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> str:
    response = await client.get(
        f"{settings.catalog_service_url}/internal/v1/catalog/pack-versions/{pack_version_id}",
        headers={"X-User-Id": str(user_id)},
        timeout=30,
    )
    response.raise_for_status()
    return PackVersionContext.model_validate(response.json()).disk_path


async def publish_lab_job(
    channel: AbstractChannel,
    settings: GradingSettings,
    *,
    lab_run_id: uuid.UUID,
    attempt_id: uuid.UUID,
    pack_root: str,
    step: dict[str, object],
) -> None:
    await declare_queue(channel, settings.lab_jobs_queue)
    await publish_json(
        channel,
        settings.lab_jobs_queue,
        {
            "lab_run_id": str(lab_run_id),
            "attempt_id": str(attempt_id),
            "pack_root": pack_root,
            "step": step,
        },
    )


async def _persist_lab_result(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    passed: bool,
    score: float,
    details: dict[str, object],
    duration_ms: int,
) -> None:
    row = await get_lab_result(session, attempt_id)
    if row is None:
        session.add(
            GradingResult(
                attempt_id=attempt_id,
                checker="lab",
                passed=passed,
                score=score,
                details=details,
                duration_ms=duration_ms,
            )
        )
    else:
        row.passed = passed
        row.score = score
        row.duration_ms = duration_ms
        row.details = details
    await session.commit()


def _result_details(
    details: dict[str, object],
    *,
    feedback: str | None,
    status: str,
) -> dict[str, object]:
    merged = {**details, "status": status}
    if feedback:
        merged["feedback"] = feedback
    return merged
