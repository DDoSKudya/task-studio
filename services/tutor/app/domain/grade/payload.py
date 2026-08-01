from __future__ import annotations

from typing import Any


def normalize_grade_payload(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    passed = data.get("passed")
    if not isinstance(passed, bool):
        return None
    confidence = data.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, int | float):
        return None
    conf = float(confidence)
    if conf < 0.0 or conf > 1.0:
        return None
    feedback = data.get("feedback")
    if not isinstance(feedback, str) or not feedback.strip():
        return None
    rationale = data.get("rationale")
    return {
        "passed": passed,
        "confidence": conf,
        "feedback": feedback.strip()[:500],
        "rationale": rationale.strip()[:500] if isinstance(rationale, str) else "",
    }


def parse_grade_json(raw: str) -> dict[str, Any] | None:
    from app.domain.json_util.repair import extract_json_object

    return normalize_grade_payload(extract_json_object(raw))
