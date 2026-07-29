from __future__ import annotations

import uuid

import httpx
from app.config import SessionsSettings
from app.domain.session_errors import SessionError, SubmitOutcome
from app.domain.session_grade_submit import submit_gradable
from app.domain.session_lab_submit import lab_should_sync_llm, submit_lab
from app.infra.models import Session
from sqlalchemy.ext.asyncio import AsyncSession


async def submit_lab_step(
    session: AsyncSession,
    user_id: uuid.UUID,
    learning_session: Session,
    submission: dict[str, object],
    *,
    step: dict[str, object],
    settings: SessionsSettings,
    client: httpx.AsyncClient,
) -> SubmitOutcome:
    if lab_should_sync_llm(step):
        return await submit_gradable(
            session,
            user_id,
            learning_session,
            submission,
            step={**step, "kind": "lab"},
            settings=settings,
            client=client,
        )
    try:
        return await submit_lab(
            session,
            user_id,
            learning_session,
            submission,
            step=step,
            settings=settings,
            client=client,
        )
    except SessionError as exc:
        if exc.status_code not in {503, 502}:
            raise
                                                                                  
        await session.rollback()
        return await submit_gradable(
            session,
            user_id,
            learning_session,
            submission,
            step={**step, "kind": "lab"},
            settings=settings,
            client=client,
        )
