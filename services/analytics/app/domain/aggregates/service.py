from __future__ import annotations

from app.datetime_utils import ensure_utc
from app.domain.aggregates.writers import (
    attempt_payload,
    increment_daily_progress,
    record_attempt_timeline,
    record_study_skip,
)
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.analytics_schemas import AnalyticsEventMessage

SUBMIT_EVENT_TYPES = frozenset(
    {
        "quiz_answered",
        "code_submitted",
        "task_submitted",
        "lab_submitted",
    }
)

_attempt_payload = attempt_payload
_increment_daily_progress = increment_daily_progress
_record_study_skip = record_study_skip
_record_attempt_timeline = record_attempt_timeline


async def update_postgres_aggregates(session: AsyncSession, event: AnalyticsEventMessage) -> None:
    match event.event_type:
        case "session_started":
            await increment_daily_progress(
                session,
                event.user_id,
                ensure_utc(event.event_time).date(),
                sessions_started=1,
            )
        case "step_completed":
            await increment_daily_progress(
                session,
                event.user_id,
                ensure_utc(event.event_time).date(),
                steps_completed=1,
            )
        case "study_skipped":
            await record_study_skip(session, event)
        case event_type if event_type in SUBMIT_EVENT_TYPES:
            await record_attempt_timeline(session, event)
