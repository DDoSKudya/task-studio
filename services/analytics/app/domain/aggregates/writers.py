from __future__ import annotations

import uuid
from datetime import date

from app.domain.aggregates.payload import attempt_payload
from app.domain.aggregates.records import record_attempt_timeline, record_study_skip
from app.infra.models import DailyUserProgress
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "attempt_payload",
    "increment_daily_progress",
    "record_study_skip",
    "record_attempt_timeline",
]


async def increment_daily_progress(
    session: AsyncSession,
    user_id: uuid.UUID,
    day: date,
    *,
    sessions_started: int = 0,
    steps_completed: int = 0,
) -> None:
    row = await session.get(DailyUserProgress, (user_id, day))
    if row is None:
        session.add(
            DailyUserProgress(
                user_id=user_id,
                day=day,
                sessions_started=sessions_started,
                steps_completed=steps_completed,
            )
        )
        return
    row.sessions_started += sessions_started
    row.steps_completed += steps_completed
