from __future__ import annotations

from datetime import UTC, datetime

from app.infra.models import PhaseProgress, Session
from studio_contracts.manifest import PhaseName, SessionPosition


def apply_position(learning_session: Session, position: SessionPosition) -> None:
    learning_session.current_topic_id = position.topic_id
    learning_session.current_phase = position.phase
    learning_session.current_step_id = position.step_id
    learning_session.updated_at = datetime.now(UTC)


def mark_earlier_phases_complete(
    progress: PhaseProgress,
    *,
    order: tuple[PhaseName, ...],
    from_phase: PhaseName,
    to_phase: PhaseName,
) -> None:
    try:
        from_index = order.index(from_phase)
        to_index = order.index(to_phase)
    except ValueError:
        return
    if to_index <= from_index:
        return
    for phase in order[:to_index]:
        if phase == "study":
            progress.study_completed = True
        elif phase == "practice":
            progress.practice_completed = True
        elif phase == "assess":
            progress.assess_completed = True


def mark_step_completed(learning_session: Session, step_id: str) -> None:
    if not step_id:
        return
    current = list(learning_session.completed_step_ids or [])
    if step_id in current:
        return
    current.append(step_id)
    learning_session.completed_step_ids = current
    learning_session.updated_at = datetime.now(UTC)
