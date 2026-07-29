from __future__ import annotations

import uuid

from app.api.deps import DbSession
from app.api.session_views import build_session_state
from app.domain.sessions import get_owned_session
from fastapi import APIRouter
from studio_common.internal import InternalUserId
from studio_contracts.session_schemas import SessionState

router = APIRouter()


@router.get("/{session_id}", response_model=SessionState)
async def get_session(
    session_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
) -> SessionState:
    learning_session = await get_owned_session(session, user_id, session_id)
    return await build_session_state(session, learning_session)
