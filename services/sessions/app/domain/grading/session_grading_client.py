from __future__ import annotations

import uuid

import httpx
from app.config import SessionsSettings
from app.domain.common.session_errors import SessionError
from app.infra.models import Attempt
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.api.grading_schemas import GradingCheckResponse


async def call_grading(
    client: httpx.AsyncClient,
    settings: SessionsSettings,
    *,
    step: dict[str, object],
    submission: dict[str, object],
    user_id: uuid.UUID | None = None,
) -> GradingCheckResponse:
    try:
        response = await client.post(
            f"{settings.grading_service_url}/internal/v1/grading/check",
            json={
                "step": step,
                "submission": submission,
                "user_id": str(user_id) if user_id else None,
            },
        )
    except httpx.HTTPError as exc:
        raise SessionError(503, "grading unavailable") from exc
    if response.is_error:
        raise SessionError(response.status_code, upstream_error_detail(response))
    return GradingCheckResponse.model_validate(response.json())


def upstream_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return "grading failed"
    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        return payload["detail"]
    return "grading failed"


async def next_attempt_number(
    session: AsyncSession,
    session_id: uuid.UUID,
    topic_id: str,
    phase: str,
    step_id: str,
) -> int:
    result = await session.execute(
        select(func.max(Attempt.attempt_number)).where(
            Attempt.session_id == session_id,
            Attempt.topic_id == topic_id,
            Attempt.phase == phase,
            Attempt.step_id == step_id,
        )
    )
    current = result.scalar_one_or_none()
    return 1 if current is None else current + 1


async def create_attempt(
    session: AsyncSession,
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    topic_id: str,
    phase: str,
    step_id: str,
    submission: dict[str, object],
    result: dict[str, object] | None = None,
    retries: int = 3,
) -> Attempt:
    last_error: IntegrityError | None = None
    for _ in range(retries):
        attempt_number = await next_attempt_number(session, session_id, topic_id, phase, step_id)
        attempt = Attempt(
            session_id=session_id,
            user_id=user_id,
            topic_id=topic_id,
            phase=phase,
            step_id=step_id,
            attempt_number=attempt_number,
            submission=submission,
            result=result,
        )
        try:
            async with session.begin_nested():
                session.add(attempt)
                await session.flush()
            return attempt
        except IntegrityError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error
