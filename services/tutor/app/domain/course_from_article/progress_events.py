from __future__ import annotations

import json


def _stage_event(
    *,
    stage: str,
    status: str,
    progress: float,
    message: str,
    message_key: str | None = None,
    message_params: dict[str, object] | None = None,
    index: int | None = None,
    total: int | None = None,
    detail: dict[str, object] | None = None,
) -> dict[str, object]:
    event: dict[str, object] = {
        "type": "stage",
        "stage": stage,
        "status": status,
        "progress": round(min(1.0, max(0.0, progress)), 4),
        "message": message,
    }
    if message_key is not None:
        event["message_key"] = message_key
    if message_params is not None:
        event["message_params"] = message_params
    if index is not None:
        event["index"] = index
    if total is not None:
        event["total"] = total
    if detail is not None:
        event["detail"] = detail
    return event


def _band_progress(band: tuple[float, float], done: int, total: int) -> float:
    if total <= 0:
        return band[1]
    ratio = min(1.0, max(0.0, done / total))
    return band[0] + (band[1] - band[0]) * ratio


def _sse_event(payload: dict[str, object]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()
