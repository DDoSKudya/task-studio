from __future__ import annotations

import uuid

import structlog
from app.domain.common.session_errors import SessionError
from app.domain.lifecycle.session_lifecycle import (
    _get_or_create_progress,
    _require_active,
    get_owned_session,
)
from app.domain.progress.session_progress import apply_position, mark_step_completed
from app.infra.models import Session
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.packs.manifest import entry_after_phase, phase_step_ids, read_policies

log = structlog.get_logger("sessions")


async def skip_study(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Session:
    learning_session = await get_owned_session(session, user_id, session_id)
    _require_active(learning_session)

    policies = read_policies(learning_session.manifest)
    if not policies.skip_study_allowed:
        raise SessionError(403, "study skip is not allowed")

    topic_id = learning_session.current_topic_id
    progress = await _get_or_create_progress(session, learning_session.id, topic_id)
    progress.study_skipped = True
    progress.study_completed = True

    for study_step_id in phase_step_ids(learning_session.manifest, topic_id, "study"):
        mark_step_completed(learning_session, study_step_id)

    try:
        position = entry_after_phase(learning_session.manifest, topic_id, "study")
    except ValueError as exc:
        raise SessionError(422, str(exc)) from exc

    apply_position(learning_session, position)
    await session.commit()
    await session.refresh(learning_session)

    log.info(
        "study_skipped",
        session_id=str(learning_session.id),
        user_id=str(user_id),
        topic_id=topic_id,
    )
    return learning_session
