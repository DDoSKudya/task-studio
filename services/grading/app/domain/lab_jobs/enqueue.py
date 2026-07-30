from __future__ import annotations

import uuid

import structlog
from app.config import GradingSettings
from app.domain.check.outcome import GradingError
from app.domain.lab_jobs.persist import get_lab_result
from app.infra.models import GradingResult
from sqlalchemy.ext.asyncio import AsyncSession
from studio_common.rabbitmq import declare_queue, publish_json, rabbit_connection
from studio_contracts.grading_schemas import GradingLabSubmitResponse

log = structlog.get_logger("grading.lab")


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
        return GradingLabSubmitResponse(status="completed", attempt_id=str(attempt_id))

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
