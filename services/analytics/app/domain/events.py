from __future__ import annotations

import asyncio
import uuid
from datetime import date

import structlog
from app.datetime_utils import ensure_utc
from app.infra.clickhouse import insert_event
from app.infra.models import (
    AttemptTimelineRow,
    DailyUserProgress,
    ProcessedEvent,
    StudySkipCount,
    TopicAssessScore,
)
from clickhouse_connect.driver.client import Client
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.analytics_schemas import AnalyticsEventMessage

log = structlog.get_logger("analytics.events")

SUBMIT_EVENT_TYPES = frozenset({"quiz_answered", "code_submitted"})


class PermanentEventError(Exception):
    pass


def parse_event_message(payload: dict[str, object]) -> AnalyticsEventMessage:
    try:
        return AnalyticsEventMessage.model_validate(payload)
    except ValidationError as exc:
        raise PermanentEventError("invalid event payload") from exc


async def process_event(
    session: AsyncSession,
    client: Client,
    database: str,
    event: AnalyticsEventMessage,
) -> None:
    if await session.get(ProcessedEvent, event.event_id) is not None:
        return

    await asyncio.to_thread(insert_event, client, database, event)
    await _update_postgres_aggregates(session, event)
    session.add(ProcessedEvent(event_id=event.event_id))
    await session.commit()
    log.info(
        "analytics_event_stored",
        event_id=str(event.event_id),
        event_type=event.event_type,
        user_id=str(event.user_id),
    )


async def _update_postgres_aggregates(session: AsyncSession, event: AnalyticsEventMessage) -> None:
    match event.event_type:
        case "session_started":
            await _increment_daily_progress(
                session,
                event.user_id,
                _event_day(event),
                sessions_started=1,
            )
        case "step_completed":
            await _increment_daily_progress(
                session,
                event.user_id,
                _event_day(event),
                steps_completed=1,
            )
        case "study_skipped":
            await _record_study_skip(session, event)
        case event_type if event_type in SUBMIT_EVENT_TYPES:
            await _record_assess_attempt(session, event)
            await _record_attempt_timeline(session, event)


def _event_day(event: AnalyticsEventMessage) -> date:
    return ensure_utc(event.event_time).date()


def _attempt_payload(event: AnalyticsEventMessage) -> tuple[uuid.UUID, float] | None:
    attempt_raw = event.payload.get("attempt_id")
    score_raw = event.payload.get("score")
    if not isinstance(attempt_raw, str) or not isinstance(score_raw, (int, float)):
        return None
    try:
        return uuid.UUID(attempt_raw), float(score_raw)
    except ValueError:
        return None


async def _increment_daily_progress(
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


async def _record_study_skip(session: AsyncSession, event: AnalyticsEventMessage) -> None:
    row = await session.get(
        StudySkipCount,
        (event.user_id, event.session_id, event.topic_id),
    )
    skipped_at = ensure_utc(event.event_time)
    if row is None:
        session.add(
            StudySkipCount(
                user_id=event.user_id,
                session_id=event.session_id,
                pack_version_id=event.pack_version_id,
                pack_title=event.pack_title,
                topic_id=event.topic_id,
                skip_count=1,
                last_skipped_at=skipped_at,
            )
        )
        return
    row.skip_count += 1
    row.last_skipped_at = skipped_at
    if event.pack_title:
        row.pack_title = event.pack_title


async def _record_assess_attempt(session: AsyncSession, event: AnalyticsEventMessage) -> None:
    if event.phase != "assess":
        return
    payload = _attempt_payload(event)
    if payload is None:
        return
    _, score = payload

    row = await session.get(
        TopicAssessScore,
        (event.user_id, event.session_id, event.topic_id),
    )
    event_time = ensure_utc(event.event_time)
    if row is None:
        session.add(
            TopicAssessScore(
                user_id=event.user_id,
                session_id=event.session_id,
                pack_version_id=event.pack_version_id,
                topic_id=event.topic_id,
                best_score=score,
                attempt_count=1,
                last_event_at=event_time,
            )
        )
        return
    row.attempt_count += 1
    row.best_score = max(float(row.best_score), score)
    row.last_event_at = event_time


async def _record_attempt_timeline(session: AsyncSession, event: AnalyticsEventMessage) -> None:
    payload = _attempt_payload(event)
    if payload is None:
        return
    attempt_id, score = payload
    passed_raw = event.payload.get("passed")
    if not isinstance(passed_raw, bool):
        return
    if await session.get(AttemptTimelineRow, attempt_id) is not None:
        return

    session.add(
        AttemptTimelineRow(
            attempt_id=attempt_id,
            user_id=event.user_id,
            session_id=event.session_id,
            pack_title=event.pack_title,
            topic_id=event.topic_id,
            phase=event.phase,
            step_id=event.step_id,
            passed=passed_raw,
            score=score,
            created_at=ensure_utc(event.event_time),
        )
    )
