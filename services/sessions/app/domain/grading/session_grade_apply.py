from __future__ import annotations

from app.domain.lifecycle.session_lifecycle import _get_or_create_progress
from app.domain.progress.session_gating import (
    _session_completed,
    _topic_assess_passed,
    _topic_practice_passed,
)
from app.infra.models import Attempt, Session
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.api.grading_schemas import GradingCheckResponse


async def apply_grading_result(
    session: AsyncSession,
    learning_session: Session,
    grading: GradingCheckResponse,
    *,
    attempt: Attempt | None = None,
) -> bool:
    topic_id = attempt.topic_id if attempt is not None else learning_session.current_topic_id
    phase = attempt.phase if attempt is not None else learning_session.current_phase

    progress = await _get_or_create_progress(
        session,
        learning_session.id,
        topic_id,
    )

    if grading.passed:
        if phase == "practice":
            if await _topic_practice_passed(session, learning_session, topic_id=topic_id):
                progress.practice_completed = True
        elif phase == "assess":
            best = progress.assess_best_score
            if best is None:
                progress.assess_best_score = grading.score
            else:
                progress.assess_best_score = max(float(best), grading.score)
            if await _topic_assess_passed(session, learning_session, topic_id=topic_id):
                progress.assess_completed = True
    elif phase == "practice":
        progress.practice_completed = await _topic_practice_passed(
            session, learning_session, topic_id=topic_id
        )
    elif phase == "assess":
        progress.assess_completed = await _topic_assess_passed(
            session, learning_session, topic_id=topic_id
        )

    if await _session_completed(session, learning_session):
        learning_session.status = "completed"
    elif learning_session.status == "completed":
        learning_session.status = "active"

    return bool(grading.passed)
