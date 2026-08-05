from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.session_errors import SessionError
from app.infra.models import Session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer


async def active_sessions_for_pack(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> list[Session]:
    result = await session.execute(
        select(Session)
        .where(
            Session.user_id == user_id,
            Session.pack_version_id == pack_version_id,
            Session.status == "active",
        )
        .order_by(Session.updated_at.desc())
    )
    return list(result.scalars())


async def get_owned_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> Session:
    learning_session = await session.get(Session, session_id)
    if learning_session is None or learning_session.user_id != user_id:
        raise SessionError(404, "session not found")
    return learning_session


def require_active(learning_session: Session) -> None:
    if learning_session.status != "active":
        raise SessionError(409, "session is not active")


async def abandon_sessions_for_pack_versions(
    session: AsyncSession,
    user_id: uuid.UUID,
    pack_version_ids: list[uuid.UUID],
    *,
    pack_titles: list[str] | None = None,
) -> int:
    del pack_titles
    if not pack_version_ids:
        return 0

    result = await session.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.status != "abandoned",
            Session.pack_version_id.in_(pack_version_ids),
        )
    )
    rows = list(result.scalars())
    for learning_session in rows:
        learning_session.status = "abandoned"
        learning_session.updated_at = datetime.now(UTC)
    if rows:
        await session.commit()
    return len(rows)


async def list_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[Session]:
    result = await session.execute(
        select(Session)
        .options(defer(Session.manifest))
        .where(Session.user_id == user_id)
        .order_by(Session.updated_at.desc())
        .limit(200)
    )
    return list(result.scalars())
