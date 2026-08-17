from __future__ import annotations

import re
from typing import Any

from app.domain.stepik_quiz.constants import _RUNTIME_TO_STEPIK


def _code_reply_candidates(
    step: dict[str, object],
    source: str,
    attempt: dict[str, Any],
) -> list[dict[str, Any]]:
    cleaned = source.strip()
    mode = str(step.get("stepik_reply") or "").casefold()
    runtime = str(step.get("runtime") or "").casefold()
    replies: list[dict[str, Any]] = []

    def _add(reply: dict[str, Any]) -> None:
        if reply not in replies:
            replies.append(reply)

    wants_sql = mode in {"solve_sql", "sql"} or runtime == "sql"
    if wants_sql:
        _add({"solve_sql": cleaned})

    if mode == "text":
        _add({"text": cleaned})

    if mode in {"", "code"} or not wants_sql:
        for language in _code_language_candidates(step, attempt):
            _add({"language": language, "code": cleaned})

    if not replies:
        _add({"solve_sql": cleaned})
        _add({"language": "sql", "code": cleaned})
    return replies


def _code_language_candidates(step: dict[str, object], attempt: dict[str, Any]) -> list[str]:
    candidates: list[str] = []

    def _add(value: object) -> None:
        if isinstance(value, str) and value.strip():
            cleaned = value.strip()
            if cleaned not in candidates:
                candidates.append(cleaned)

    _add(step.get("stepik_language"))
    runtime = step.get("runtime")
    if isinstance(runtime, str):
        _add(_RUNTIME_TO_STEPIK.get(runtime.casefold(), runtime))
        _add(runtime)

    dataset = attempt.get("dataset") if isinstance(attempt.get("dataset"), dict) else {}
    for key in ("languages", "available_languages"):
        rows = dataset.get(key) if isinstance(dataset, dict) else None
        if isinstance(rows, list):
            for item in rows:
                _add(item)

    for fallback in ("sql", "python3", "python"):
        _add(fallback)
    return candidates


def _submission_feedback(submission: dict[str, Any], *, fallback: str | None) -> str | None:
    for key in ("hint", "feedback"):
        value = submission.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            message = value.get("message") or value.get("text")
            if isinstance(message, str) and message.strip():
                return message.strip()
    return fallback


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()
