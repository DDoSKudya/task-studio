from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(value: datetime | None) -> datetime:
    event_time = value or datetime.now(UTC)
    if event_time.tzinfo is None:
        return event_time.replace(tzinfo=UTC)
    return event_time
