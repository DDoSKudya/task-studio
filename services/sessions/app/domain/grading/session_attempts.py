from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.common.session_errors import SessionError, SubmitOutcome
from app.domain.grading.session_grade_submit import apply_grading_result
from app.domain.lifecycle.session_lifecycle import get_owned_session
from app.infra.models import Attempt, Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.api.grading_schemas import GradingCheckResponse


async def complete_attempt(
    session: AsyncSession,
    attempt_id: uuid.UUID,
    *,
    passed: bool,
    score: float,
    feedback: str | None,
    details: dict[str, object],
) -> SubmitOutcome:
    result = await session.execute(select(Attempt).where(Attempt.id == attempt_id))
    attempt = result.scalar_one_or_none()
    if attempt is None:
        raise SessionError(404, "attempt not found")

    owner = details.get("user_id")
    if isinstance(owner, str) and owner.strip():
        try:
            if uuid.UUID(owner) != attempt.user_id:
                raise SessionError(403, "attempt owner mismatch")
        except ValueError as exc:
            raise SessionError(422, "invalid user_id in details") from exc

    learning_session = await session.get(Session, attempt.session_id)
    if learning_session is None:
        raise SessionError(404, "session not found")

    grading = GradingCheckResponse(
        passed=passed,
        score=score,
        feedback=feedback,
        details=details,
    )

    if learning_session.status != "active":
        return SubmitOutcome(
            attempt=attempt,
            grading=grading,
            phase_completed=False,
            status="completed",
            learning_session=learning_session,
        )

    attempt.result = grading.model_dump(mode="json")
    phase_completed = await apply_grading_result(
        session, learning_session, grading, attempt=attempt
    )
    learning_session.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(attempt)
    return SubmitOutcome(
        attempt=attempt,
        grading=grading,
        phase_completed=phase_completed,
        status="completed",
        learning_session=learning_session,
    )


async def list_attempts(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> list[Attempt]:
    learning_session = await get_owned_session(session, user_id, session_id)
    result = await session.execute(
        select(Attempt)
        .where(Attempt.session_id == learning_session.id)
        .order_by(Attempt.created_at.desc())
    )
    return list(result.scalars())


async def get_attempt(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    attempt_id: uuid.UUID,
) -> Attempt:
    learning_session = await get_owned_session(session, user_id, session_id)
    result = await session.execute(
        select(Attempt).where(
            Attempt.id == attempt_id,
            Attempt.session_id == learning_session.id,
        )
    )
    attempt = result.scalar_one_or_none()
    if attempt is None:
        raise SessionError(404, "attempt not found")
    return attempt
