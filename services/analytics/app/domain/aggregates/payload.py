from __future__ import annotations

import uuid

from studio_contracts.api.analytics_schemas import AnalyticsEventMessage


def attempt_payload(event: AnalyticsEventMessage) -> tuple[uuid.UUID, float] | None:
    attempt_raw = event.payload.get("attempt_id")
    score_raw = event.payload.get("score")
    if not isinstance(attempt_raw, str) or not isinstance(score_raw, int | float):
        return None
    try:
        return uuid.UUID(attempt_raw), float(score_raw)
    except ValueError:
        return None
