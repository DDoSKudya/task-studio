from __future__ import annotations

import asyncio
import uuid

import httpx
import structlog
from app.config import GradingSettings
from app.domain.lab_jobs.enqueue import enqueue_lab_job
from app.domain.lab_jobs.persist import get_lab_result, persist_lab_result, result_details
from sqlalchemy.ext.asyncio import AsyncSession
from studio_common.system_auth import system_token_headers

log = structlog.get_logger("grading.lab")

__all__ = [
    "get_lab_result",
    "enqueue_lab_job",
    "complete_lab_job",
]

_CALLBACK_ATTEMPTS = 3


async def _post_sessions_complete(
    client: httpx.AsyncClient,
    settings: GradingSettings,
    *,
    attempt_id: uuid.UUID,
    passed: bool,
    score: float,
    feedback: str | None,
    details: dict[str, object],
) -> None:
    url = f"{settings.sessions_service_url}/internal/v1/sessions/attempts/{attempt_id}/complete"
    body = {
        "passed": passed,
        "score": score,
        "feedback": feedback,
        "details": details,
    }
    headers = system_token_headers()
    last_error: Exception | None = None
    for attempt in range(1, _CALLBACK_ATTEMPTS + 1):
        try:
            response = await client.post(url, json=body, headers=headers, timeout=30)
            if response.status_code in {200, 204, 409}:
                return
            response.raise_for_status()
            return
        except httpx.HTTPError as exc:
            last_error = exc
            log.warning(
                "lab_sessions_callback_failed",
                attempt_id=str(attempt_id),
                try_number=attempt,
                error=str(last_error),
                error_type=type(last_error).__name__,
            )
            if attempt < _CALLBACK_ATTEMPTS:
                await asyncio.sleep(0.4 * attempt)
    if last_error is None:
        raise RuntimeError("lab sessions callback failed")
    raise last_error


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
    body_details = dict(details)
    existing = await get_lab_result(session, attempt_id)
    if existing is not None and isinstance(existing.details, dict):
        prior_user = existing.details.get("user_id")
        if isinstance(prior_user, str) and prior_user.strip():
            body_details.setdefault("user_id", prior_user)

    await _post_sessions_complete(
        client,
        settings,
        attempt_id=attempt_id,
        passed=passed,
        score=score,
        feedback=feedback,
        details=body_details,
    )

    await persist_lab_result(
        session,
        attempt_id,
        passed=passed,
        score=score,
        details=result_details(details, feedback=feedback, status="completed"),
        duration_ms=duration_ms,
    )
    log.info("lab_job_completed", attempt_id=str(attempt_id), passed=passed)
