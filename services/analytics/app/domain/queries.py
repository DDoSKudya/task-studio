from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.datetime_utils import ensure_utc
from app.infra.models import AttemptTimelineRow, DailyUserProgress, StudySkipCount
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.analytics_schemas import (
    AttemptsTimelineResponse,
    AttemptTimelineEntry,
    DailyProgressPoint,
    ProgressResponse,
    SkipsResponse,
    StudySkipEntry,
)


async def get_progress(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    days: int = 30,
) -> ProgressResponse:
    since = datetime.now(UTC).date() - timedelta(days=max(days - 1, 0))
    result = await session.execute(
        select(DailyUserProgress)
        .where(DailyUserProgress.user_id == user_id, DailyUserProgress.day >= since)
        .order_by(DailyUserProgress.day.asc())
    )
    rows = result.scalars().all()
    points = [
        DailyProgressPoint(
            day=datetime.combine(row.day, datetime.min.time(), tzinfo=UTC),
            sessions_started=row.sessions_started,
            steps_completed=row.steps_completed,
        )
        for row in rows
    ]
    return ProgressResponse(
        points=points,
        total_sessions=sum(point.sessions_started for point in points),
        total_steps_completed=sum(point.steps_completed for point in points),
    )


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
    if cursor and (cursor_time := _parse_cursor(cursor)) is not None:
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


def _parse_cursor(cursor: str) -> datetime | None:
    try:
        return ensure_utc(datetime.fromisoformat(cursor.replace("Z", "+00:00")))
    except ValueError:
        return None
