from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from app.config import SessionsSettings
from app.domain.session_create import create_new_session
from app.domain.session_queries import (
    abandon_sessions_for_pack_versions,
    active_sessions_for_pack,
    get_owned_session,
    list_sessions,
    require_active,
)
from app.infra.models import PhaseProgress, Session
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "start_session",
    "get_owned_session",
    "abandon_sessions_for_pack_versions",
    "list_sessions",
    "_require_active",
    "_get_or_create_progress",
    "_active_sessions_for_pack",
]

_require_active = require_active
_active_sessions_for_pack = active_sessions_for_pack


async def start_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
    *,
    settings: SessionsSettings,
    client: httpx.AsyncClient,
) -> tuple[Session, bool]:
\
\
\
\
       
    existing = await active_sessions_for_pack(session, user_id, pack_version_id)
    if existing:
        primary, *duplicates = existing
        now = datetime.now(UTC)
        primary.updated_at = now
        for duplicate in duplicates:
            duplicate.status = "abandoned"
            duplicate.updated_at = now
        await session.commit()
        await session.refresh(primary)
        return primary, False

    learning_session = await create_new_session(
        session,
        user_id,
        pack_version_id,
        settings=settings,
        client=client,
    )
    return learning_session, True


async def _get_or_create_progress(
    session: AsyncSession,
    session_id: uuid.UUID,
    topic_id: str,
) -> PhaseProgress:
    progress = await session.get(PhaseProgress, (session_id, topic_id))
    if progress is None:
        progress = PhaseProgress(session_id=session_id, topic_id=topic_id)
        session.add(progress)
        await session.flush()
    return progress
