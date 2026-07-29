from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.session_errors import SessionError
from app.infra.models import Session
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


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
    titles = [title.strip() for title in (pack_titles or []) if title and title.strip()]
    if not pack_version_ids and not titles:
        return 0

    filters = [Session.user_id == user_id, Session.status != "abandoned"]
    version_or_title = []
    if pack_version_ids:
        version_or_title.append(Session.pack_version_id.in_(pack_version_ids))
    if titles:
        version_or_title.append(Session.pack_title.in_(titles))
    if len(version_or_title) == 1:
        filters.append(version_or_title[0])
    else:
        filters.append(or_(*version_or_title))

    result = await session.execute(select(Session).where(*filters))
    rows = list(result.scalars())
    for learning_session in rows:
        learning_session.status = "abandoned"
        learning_session.updated_at = datetime.now(UTC)
    if rows:
        await session.commit()
    return len(rows)


async def list_sessions(session: AsyncSession, user_id: uuid.UUID) -> list[Session]:
    result = await session.execute(
        select(Session).where(Session.user_id == user_id).order_by(Session.updated_at.desc())
    )
    return list(result.scalars())
