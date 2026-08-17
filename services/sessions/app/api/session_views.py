from __future__ import annotations

from app.api.deps import DbSession, load_progress
from app.api.mappers import session_state
from app.domain.queries.sessions import list_passed_step_ids
from app.infra.models import Session
from studio_contracts.api.session_schemas import SessionState


async def build_session_state(session: DbSession, learning_session: Session) -> SessionState:
    progress_rows = await load_progress(session, learning_session.id)
    passed = await list_passed_step_ids(session, learning_session.id)
    return session_state(
        learning_session,
        progress_rows,
        passed_step_ids=passed,
    )


def session_position(learning_session: Session) -> tuple[str, str, str]:
    return (
        learning_session.current_topic_id,
        learning_session.current_phase,
        learning_session.current_step_id,
    )
