from __future__ import annotations

import uuid

import httpx
import structlog
from app.config import GradingSettings
from app.domain.lab_jobs.enqueue import enqueue_lab_job
from app.domain.lab_jobs.persist import get_lab_result, persist_lab_result, result_details
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger("grading.lab")

__all__ = [
    "get_lab_result",
    "enqueue_lab_job",
    "complete_lab_job",
]


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
    await persist_lab_result(
        session,
        attempt_id,
        passed=passed,
        score=score,
        details=result_details(details, feedback=feedback, status="completed"),
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
