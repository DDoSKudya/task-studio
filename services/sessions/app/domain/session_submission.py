from __future__ import annotations

import uuid

import httpx
from app.config import SessionsSettings
from app.domain.session_attempts import complete_attempt, list_attempts
from app.domain.session_errors import SubmitOutcome
from app.domain.session_grade_submit import submit_gradable
from app.domain.session_lab_route import submit_lab_step
from app.domain.session_lifecycle import _require_active, get_owned_session
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.manifest import get_step

__all__ = [
    "submit_step",
    "complete_attempt",
    "list_attempts",
]


async def submit_step(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    submission: dict[str, object],
    *,
    settings: SessionsSettings,
    client: httpx.AsyncClient,
) -> SubmitOutcome:
    learning_session = await get_owned_session(session, user_id, session_id)
    _require_active(learning_session)

    step = get_step(learning_session.manifest, learning_session.current_step_id)
    kind = step.get("kind")
    if kind == "lab":
        return await submit_lab_step(
            session,
            user_id,
            learning_session,
            submission,
            step=step,
            settings=settings,
            client=client,
        )
    if kind not in {"quiz", "code", "task"}:
        return await submit_gradable(
            session,
            user_id,
            learning_session,
            submission,
            step=step if isinstance(step, dict) else {"kind": "task"},
            settings=settings,
            client=client,
        )

    return await submit_gradable(
        session,
        user_id,
        learning_session,
        submission,
        step=step,
        settings=settings,
        client=client,
    )
