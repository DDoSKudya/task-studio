from __future__ import annotations

import uuid

import httpx
from app.config import GradingSettings
from app.domain.check import check_submission, parse_attempt_id
from app.infra.models import GradingResult
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.grading_schemas import GradingCheckRequest, GradingCheckResponse


async def run_and_store_check(
    session: AsyncSession,
    body: GradingCheckRequest,
    *,
    settings: GradingSettings,
    client: httpx.AsyncClient,
) -> GradingCheckResponse:
    attempt_id = parse_attempt_id(body.submission)
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
    await session.commit()
    return outcome.to_response()
