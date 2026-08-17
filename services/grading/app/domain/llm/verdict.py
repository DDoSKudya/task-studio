from __future__ import annotations

import time

from app.domain.check.outcome import CheckOutcome
from studio_contracts.api.tutor_schemas import TutorGradeResponse

_SOFT_ACCEPT_FLOOR = 0.55


def outcome_from_tutor_verdict(
    verdict: TutorGradeResponse,
    *,
    started: float,
    min_confidence: float,
    prior_feedback: str | None = None,
    prior_checker: str | None = None,
) -> CheckOutcome | None:
    if not verdict.usable:
        return None

    soft = False
    if verdict.confidence < min_confidence:
        if verdict.confidence < _SOFT_ACCEPT_FLOOR:
            return None
        soft = True

    details: dict[str, object] = {
        "gradable": True,
        "checker": "llm",
        "confidence": verdict.confidence,
        "model": verdict.model,
    }
    if soft:
        details["soft_accept"] = True
    if verdict.rationale:
        details["rationale"] = verdict.rationale
    if prior_feedback:
        details["prior_feedback"] = prior_feedback
    if prior_checker:
        details["prior_checker"] = prior_checker

    feedback = verdict.feedback.strip() or None
    if verdict.passed and not feedback:
        feedback = "Checked by AI grader"

    return CheckOutcome(
        passed=verdict.passed,
        score=1.0 if verdict.passed else 0.0,
        feedback=feedback,
        details=details,
        checker="llm",
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
