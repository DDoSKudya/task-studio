from __future__ import annotations

import uuid

from app.domain.queries.attempts_timeline import get_attempts_timeline
from app.domain.queries.progress import get_progress
from app.infra.models import StudySkipCount
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.analytics_schemas import SkipsResponse, StudySkipEntry

__all__ = [
    "get_progress",
    "get_skips",
    "get_attempts_timeline",
]


async def get_skips(session: AsyncSession, user_id: uuid.UUID) -> SkipsResponse:
    result = await session.execute(
        select(StudySkipCount)
        .where(StudySkipCount.user_id == user_id)
        .order_by(desc(StudySkipCount.last_skipped_at))
    )
    rows = result.scalars().all()
    items = [
        StudySkipEntry(
            session_id=row.session_id,
            pack_version_id=row.pack_version_id,
            pack_title=row.pack_title,
            topic_id=row.topic_id,
            skipped_at=row.last_skipped_at,
        )
        for row in rows
    ]
    return SkipsResponse(items=items, total=len(items))
