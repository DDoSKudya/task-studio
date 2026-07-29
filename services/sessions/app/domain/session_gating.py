from __future__ import annotations

from app.domain.session_completion import session_completed, topic_practice_passed
from app.domain.session_errors import SessionError
from app.domain.session_gate_leave import ensure_can_leave_gated_step, position_index
from app.domain.session_passed import list_passed_step_ids
from app.infra.models import Attempt, Session
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.manifest import PackPolicies

__all__ = [
    "list_passed_step_ids",
    "_ensure_assess_attempt_allowed",
    "_ensure_can_leave_gated_step",
    "_session_completed",
    "_topic_practice_passed",
]

_session_completed = session_completed
_topic_practice_passed = topic_practice_passed
_ensure_can_leave_gated_step = ensure_can_leave_gated_step
_position_index = position_index


async def _ensure_assess_attempt_allowed(
    session: AsyncSession,
    learning_session: Session,
    policies: PackPolicies,
) -> None:
    if policies.assess_max_attempts is None:
        return
    result = await session.execute(
        select(func.count())
        .select_from(Attempt)
        .where(
            Attempt.session_id == learning_session.id,
            Attempt.topic_id == learning_session.current_topic_id,
            Attempt.phase == "assess",
            Attempt.step_id == learning_session.current_step_id,
        )
    )
    count = result.scalar_one()
    if count >= policies.assess_max_attempts:
        raise SessionError(409, "assess attempt limit reached")
