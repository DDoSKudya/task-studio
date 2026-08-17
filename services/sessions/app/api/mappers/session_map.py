from __future__ import annotations

from typing import cast

from app.api.mappers.session_map_bits import attempt_info, phase_progress
from app.api.mappers.session_outline import build_outline
from app.infra.models import PhaseProgress, Session
from studio_contracts.api.session_schemas import SessionState, SessionStatus, SessionSummary
from studio_contracts.packs.manifest import PhaseName, read_policies

__all__ = [
    "session_summary",
    "session_state",
    "build_outline",
    "phase_progress",
    "attempt_info",
]


def session_summary(learning_session: Session) -> SessionSummary:
    return SessionSummary(
        id=learning_session.id,
        pack_version_id=learning_session.pack_version_id,
        pack_title=learning_session.pack_title,
        status=cast(SessionStatus, learning_session.status),
        current_topic_id=learning_session.current_topic_id,
        current_phase=cast(PhaseName, learning_session.current_phase),
        current_step_id=learning_session.current_step_id,
        started_at=learning_session.started_at,
        updated_at=learning_session.updated_at,
    )


def session_state(
    learning_session: Session,
    progress_rows: list[PhaseProgress],
    *,
    passed_step_ids: list[str] | None = None,
) -> SessionState:
    policies = read_policies(learning_session.manifest)
    completed = list(learning_session.completed_step_ids or [])
    return SessionState(
        id=learning_session.id,
        pack_version_id=learning_session.pack_version_id,
        pack_title=learning_session.pack_title,
        status=cast(SessionStatus, learning_session.status),
        current_topic_id=learning_session.current_topic_id,
        current_phase=cast(PhaseName, learning_session.current_phase),
        current_step_id=learning_session.current_step_id,
        policies=policies,
        phase_progress=[phase_progress(row) for row in progress_rows],
        outline=build_outline(learning_session.manifest),
        passed_step_ids=list(passed_step_ids or []),
        completed_step_ids=completed,
        started_at=learning_session.started_at,
        updated_at=learning_session.updated_at,
    )
