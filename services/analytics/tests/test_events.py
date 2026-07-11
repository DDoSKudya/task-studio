from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from studio_contracts.analytics_schemas import AnalyticsEventMessage
from support import load_analytics_module

events = load_analytics_module("app.domain.events")
parse_event_message = events.parse_event_message
process_event = events.process_event
PermanentEventError = events.PermanentEventError


def test_parse_event_message_rejects_invalid_payload() -> None:
    with pytest.raises(PermanentEventError):
        parse_event_message({"event_type": "session_started"})


@pytest.mark.asyncio
async def test_process_event_is_idempotent() -> None:
    event_id = uuid.uuid4()
    event = AnalyticsEventMessage(
        event_id=event_id,
        event_type="study_skipped",
        user_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        pack_version_id=uuid.uuid4(),
        pack_title="Demo",
        topic_id="t1",
        phase="study",
        step_id="s1",
        event_time=datetime.now(UTC),
    )

    processed = MagicMock()
    seen = False

    async def mock_get(model, _key):  # noqa: ANN001
        nonlocal seen
        if getattr(model, "__tablename__", None) == "processed_events":
            if seen:
                return processed
            seen = True
            return None
        return None

    session = AsyncMock()
    session.get = AsyncMock(side_effect=mock_get)
    session.add = MagicMock()
    session.commit = AsyncMock()

    client = MagicMock()
    await process_event(session, client, "analytics", event)
    await process_event(session, client, "analytics", event)

    assert session.commit.await_count == 1
