from __future__ import annotations

from app.domain.session_gating import (
    _session_completed,
    _topic_practice_passed,
)
from app.domain.session_lifecycle import _get_or_create_progress
from app.infra.models import Session
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.grading_schemas import GradingCheckResponse


async def apply_grading_result(
    session: AsyncSession,
    learning_session: Session,
    grading: GradingCheckResponse,
) -> bool:
    if not grading.passed:
        return False

    progress = await _get_or_create_progress(
        session,
        learning_session.id,
        learning_session.current_topic_id,
    )
    phase = learning_session.current_phase
    if phase == "practice":
        if await _topic_practice_passed(session, learning_session):
            progress.practice_completed = True
    elif phase == "assess":
        progress.assess_completed = True
        best = progress.assess_best_score
        if best is None:
            progress.assess_best_score = grading.score
        else:
            progress.assess_best_score = max(float(best), grading.score)

    if await _session_completed(session, learning_session):
        learning_session.status = "completed"
    return True
