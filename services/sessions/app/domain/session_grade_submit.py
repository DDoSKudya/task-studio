from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from app.config import SessionsSettings
from app.domain.session_errors import SubmitOutcome
from app.domain.session_gating import _ensure_assess_attempt_allowed
from app.domain.session_grade_apply import apply_grading_result
from app.domain.session_grading_client import (
    call_grading,
    next_attempt_number,
    upstream_error_detail,
)
from app.infra.models import Attempt, Session
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.manifest import read_policies

__all__ = [
    "submit_gradable",
    "apply_grading_result",
    "call_grading",
    "next_attempt_number",
    "upstream_error_detail",
]


async def submit_gradable(
    session: AsyncSession,
    user_id: uuid.UUID,
    learning_session: Session,
    submission: dict[str, object],
    *,
    step: dict[str, object],
    settings: SessionsSettings,
    client: httpx.AsyncClient,
) -> SubmitOutcome:
    policies = read_policies(learning_session.manifest)
    if learning_session.current_phase == "assess":
        await _ensure_assess_attempt_allowed(session, learning_session, policies)

    attempt_number = await next_attempt_number(
        session,
        learning_session.id,
        learning_session.current_topic_id,
        learning_session.current_phase,
        learning_session.current_step_id,
    )
    attempt = Attempt(
        session_id=learning_session.id,
        user_id=user_id,
        topic_id=learning_session.current_topic_id,
        phase=learning_session.current_phase,
        step_id=learning_session.current_step_id,
        attempt_number=attempt_number,
        submission=submission,
    )
    session.add(attempt)
    await session.flush()

    grading = await call_grading(
        client,
        settings,
        step=step,
        submission={**submission, "attempt_id": str(attempt.id)},
        user_id=user_id,
    )
    attempt.result = grading.model_dump(mode="json")
    phase_completed = await apply_grading_result(session, learning_session, grading)
    learning_session.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(attempt)
    return SubmitOutcome(attempt=attempt, grading=grading, phase_completed=phase_completed)
