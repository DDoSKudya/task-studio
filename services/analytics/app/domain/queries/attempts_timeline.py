from __future__ import annotations

import uuid
from datetime import datetime

from app.datetime_utils import ensure_utc
from app.infra.models import AttemptTimelineRow
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.analytics_schemas import AttemptsTimelineResponse, AttemptTimelineEntry


def parse_timeline_cursor(cursor: str) -> datetime | None:
    try:
        return ensure_utc(datetime.fromisoformat(cursor.replace("Z", "+00:00")))
    except ValueError:
        return None


async def get_attempts_timeline(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 50,
    cursor: str | None = None,
) -> AttemptsTimelineResponse:
    query = (
        select(AttemptTimelineRow)
        .where(AttemptTimelineRow.user_id == user_id)
        .order_by(desc(AttemptTimelineRow.created_at), desc(AttemptTimelineRow.attempt_id))
        .limit(limit + 1)
    )
    if cursor and (cursor_time := parse_timeline_cursor(cursor)) is not None:
        query = query.where(AttemptTimelineRow.created_at < cursor_time)

    result = await session.execute(query)
    rows = result.scalars().all()
    page = rows[:limit]
    items = [
        AttemptTimelineEntry(
            attempt_id=row.attempt_id,
            session_id=row.session_id,
            pack_title=row.pack_title,
            topic_id=row.topic_id,
            phase=row.phase,
            step_id=row.step_id,
            passed=row.passed,
            score=float(row.score),
            created_at=row.created_at,
        )
        for row in page
    ]
    next_cursor = page[-1].created_at.isoformat() if len(rows) > limit and page else None
    return AttemptsTimelineResponse(items=items, next_cursor=next_cursor)
