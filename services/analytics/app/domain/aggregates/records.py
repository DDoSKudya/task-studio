from __future__ import annotations

from app.datetime_utils import ensure_utc
from app.domain.aggregates.payload import attempt_payload
from app.infra.models import AttemptTimelineRow, StudySkipCount
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.api.analytics_schemas import AnalyticsEventMessage


async def record_study_skip(session: AsyncSession, event: AnalyticsEventMessage) -> None:
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


async def record_attempt_timeline(session: AsyncSession, event: AnalyticsEventMessage) -> None:
    payload = attempt_payload(event)
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
