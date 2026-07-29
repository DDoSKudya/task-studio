from __future__ import annotations

import uuid
from typing import cast

from app.domain.session_errors import SessionError
from app.domain.session_gating import _ensure_can_leave_gated_step
from app.domain.session_lifecycle import (
    _get_or_create_progress,
    _require_active,
    get_owned_session,
)
from app.domain.session_progress import (
    apply_position,
    mark_earlier_phases_complete,
    mark_step_completed,
)
from app.domain.session_skip import skip_study
from app.infra.models import Session
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.manifest import PhaseName, read_policies, resolve_position

__all__ = [
    "navigate_session",
    "skip_study",
]


async def navigate_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    *,
    topic_id: str,
    phase: PhaseName,
    step_id: str,
    complete_current: bool = False,
) -> Session:
    learning_session = await get_owned_session(session, user_id, session_id)
    _require_active(learning_session)

    try:
        position = resolve_position(learning_session.manifest, topic_id, phase, step_id)
    except ValueError as exc:
        raise SessionError(422, str(exc)) from exc

    progress = await _get_or_create_progress(session, learning_session.id, topic_id)
    policies = read_policies(learning_session.manifest)
    order = policies.phase_order
    practice_before_assess = (
        "practice" in order
        and "assess" in order
        and order.index("practice") < order.index("assess")
    )
    assess_blocked = (
        phase == "assess"
        and not policies.assess_without_practice
        and practice_before_assess
        and not progress.practice_completed
    )
    if assess_blocked:
        raise SessionError(403, "practice must be completed before assess")

    if policies.require_pass_to_advance:
        await _ensure_can_leave_gated_step(
            session,
            learning_session,
            target=position,
        )

    if complete_current:
        mark_step_completed(learning_session, learning_session.current_step_id)

    mark_earlier_phases_complete(
        progress,
        order=order,
        from_phase=cast(PhaseName, learning_session.current_phase),
        to_phase=phase,
    )

    apply_position(learning_session, position)
    await session.commit()
    await session.refresh(learning_session)
    return learning_session
