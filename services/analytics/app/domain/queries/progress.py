from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

from app.infra.clickhouse import fetch_daily_progress
from app.infra.models import DailyUserProgress
from clickhouse_connect.driver.client import Client
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.analytics_schemas import DailyProgressPoint, ProgressResponse


async def get_progress(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    days: int = 30,
    clickhouse: Client | None = None,
    clickhouse_database: str | None = None,
) -> ProgressResponse:
    since = datetime.now(UTC).date() - timedelta(days=max(days - 1, 0))
    result = await session.execute(
        select(DailyUserProgress)
        .where(DailyUserProgress.user_id == user_id, DailyUserProgress.day >= since)
        .order_by(DailyUserProgress.day.asc())
    )
    rows = result.scalars().all()
    by_day: dict[date, DailyProgressPoint] = {
        row.day: DailyProgressPoint(
            day=datetime.combine(row.day, datetime.min.time(), tzinfo=UTC),
            sessions_started=row.sessions_started,
            steps_completed=row.steps_completed,
        )
        for row in rows
    }

    if clickhouse is not None and clickhouse_database:
        try:
            ch_rows = await asyncio.to_thread(
                fetch_daily_progress,
                clickhouse,
                clickhouse_database,
                user_id=user_id,
                since_day=since,
            )
        except Exception:
            ch_rows = []
        for day_raw, sessions, steps in ch_rows:
            day = day_raw if isinstance(day_raw, date) else date.fromisoformat(str(day_raw))
            existing = by_day.get(day)
            if existing is None:
                by_day[day] = DailyProgressPoint(
                    day=datetime.combine(day, datetime.min.time(), tzinfo=UTC),
                    sessions_started=sessions,
                    steps_completed=steps,
                )
                continue
            by_day[day] = DailyProgressPoint(
                day=existing.day,
                sessions_started=max(existing.sessions_started, sessions),
                steps_completed=max(existing.steps_completed, steps),
            )

    points = [by_day[day] for day in sorted(by_day)]
    return ProgressResponse(
        points=points,
        total_sessions=sum(point.sessions_started for point in points),
        total_steps_completed=sum(point.steps_completed for point in points),
    )
