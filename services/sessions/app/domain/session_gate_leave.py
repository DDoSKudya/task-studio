from __future__ import annotations

from typing import cast

from app.domain.session_errors import SessionError
from app.domain.session_passed import passed_step_ids, step_marked_ungradable
from app.infra.models import Session
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.manifest import PhaseName, SessionPosition, get_step, iter_positions


def position_index(manifest: dict[str, object], position: SessionPosition) -> int:
    for index, item in enumerate(iter_positions(manifest)):
        if (
            item.topic_id == position.topic_id
            and item.phase == position.phase
            and item.step_id == position.step_id
        ):
            return index
    return -1


async def ensure_can_leave_gated_step(
    session: AsyncSession,
    learning_session: Session,
    *,
    target: SessionPosition,
) -> None:
    current = SessionPosition(
        topic_id=learning_session.current_topic_id,
        phase=cast(PhaseName, learning_session.current_phase),
        step_id=learning_session.current_step_id,
    )
    if position_index(learning_session.manifest, target) <= position_index(
        learning_session.manifest, current
    ):
        return
    step = get_step(learning_session.manifest, current.step_id)
    kind = step.get("kind")
    if kind not in {"quiz", "code", "task"}:
        return
    passed = await passed_step_ids(session, learning_session.id)
    if current.step_id in passed:
        return
    if await step_marked_ungradable(session, learning_session.id, current.step_id):
        return
    raise SessionError(403, "complete the current task before continuing")
