from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from analytics_helpers.loaders import load_analytics_module
from studio_contracts.analytics_schemas import AnalyticsEventMessage

aggregates = load_analytics_module("app.domain.aggregates")
update_postgres_aggregates = aggregates.update_postgres_aggregates


def _event(event_type: str, **payload: object) -> AnalyticsEventMessage:
    return AnalyticsEventMessage(
        event_id=uuid.uuid4(),
        event_type=event_type,
        user_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        pack_version_id=uuid.uuid4(),
        pack_title="Local article course",
        topic_id="t1",
        phase="practice",
        step_id="s1",
        payload=dict(payload),
        event_time=datetime.now(UTC),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event_type",
    ["quiz_answered", "code_submitted", "task_submitted", "lab_submitted"],
)
async def test_submit_events_record_attempt_timeline(event_type: str) -> None:
    attempt_id = uuid.uuid4()
    event = _event(
        event_type,
        attempt_id=str(attempt_id),
        passed=True,
        score=1.0,
        attempt_number=1,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()

    await update_postgres_aggregates(session, event)

    session.add.assert_called_once()
    row = session.add.call_args.args[0]
    assert row.attempt_id == attempt_id
    assert row.pack_title == "Local article course"
    assert row.passed is True


@pytest.mark.asyncio
async def test_step_completed_increments_daily_progress() -> None:
    event = _event("step_completed")
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()

    await update_postgres_aggregates(session, event)

    session.add.assert_called_once()
    row = session.add.call_args.args[0]
    assert row.steps_completed == 1
    assert row.sessions_started == 0
