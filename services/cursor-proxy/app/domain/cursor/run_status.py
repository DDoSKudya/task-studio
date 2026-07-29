from __future__ import annotations

from typing import Any

_TERMINAL_OK = frozenset({"FINISHED", "COMPLETED", "SUCCESS"})
_TERMINAL_FAIL = frozenset({"ERROR", "CANCELLED", "CANCELED", "EXPIRED", "FAILED"})
TERMINAL_STATUSES = _TERMINAL_OK | _TERMINAL_FAIL


def run_status(payload: dict[str, Any]) -> str:
    raw = payload.get("status")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().upper()
    nested = payload.get("run")
    if isinstance(nested, dict):
        nested_status = nested.get("status")
        if isinstance(nested_status, str) and nested_status.strip():
            return nested_status.strip().upper()
    return ""


def result_text_from_payload(payload: dict[str, Any]) -> str | None:
    for key in ("result", "text"):
        text = payload.get(key)
        if isinstance(text, str) and text.strip():
            return text.strip()
    nested = payload.get("run")
    if isinstance(nested, dict):
        for key in ("result", "text"):
            text = nested.get(key)
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def is_terminal_ok(status: str) -> bool:
    return status in _TERMINAL_OK
