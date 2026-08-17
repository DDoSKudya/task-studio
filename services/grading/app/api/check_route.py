from __future__ import annotations

import uuid

import httpx
from app.config import GradingSettings
from app.domain.check import check_submission, parse_attempt_id
from app.domain.lab_jobs.persist import get_lab_result
from app.infra.models import GradingResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.api.grading_schemas import GradingCheckRequest, GradingCheckResponse


async def run_and_store_check(
    session: AsyncSession,
    body: GradingCheckRequest,
    *,
    settings: GradingSettings,
    client: httpx.AsyncClient,
) -> GradingCheckResponse:
    attempt_id = parse_attempt_id(body.submission)
    existing = await get_lab_result(session, attempt_id)
    if existing is not None:
        return _response_from_row(existing)

    user_id = uuid.UUID(body.user_id) if body.user_id else None
    outcome = await check_submission(
        body.step,
        body.submission,
        settings=settings,
        client=client,
        user_id=user_id,
    )
    session.add(
        GradingResult(
            attempt_id=attempt_id,
            checker=outcome.checker,
            passed=outcome.passed,
            score=outcome.score,
            details=outcome.details,
            duration_ms=outcome.duration_ms,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raced = await get_lab_result(session, attempt_id)
        if raced is None:
            raise
        return _response_from_row(raced)
    return outcome.to_response()


def _response_from_row(row: GradingResult) -> GradingCheckResponse:
    return GradingCheckResponse(
        passed=bool(row.passed),
        score=float(row.score),
        feedback=_feedback_from_details(row.details),
        details=dict(row.details or {}),
    )


def _feedback_from_details(details: dict[str, object] | None) -> str | None:
    if not isinstance(details, dict):
        return None
    feedback = details.get("feedback")
    if isinstance(feedback, str) and feedback.strip():
        return feedback.strip()
    return None
