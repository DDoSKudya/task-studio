from __future__ import annotations

import uuid
from dataclasses import dataclass

from studio_contracts.api.grading_schemas import GradingCheckResponse


class GradingError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    passed: bool
    score: float
    feedback: str | None
    details: dict[str, object]
    checker: str
    duration_ms: int

    def to_response(self) -> GradingCheckResponse:
        return GradingCheckResponse(
            passed=self.passed,
            score=self.score,
            feedback=self.feedback,
            details=self.details,
        )


def parse_attempt_id(submission: dict[str, object]) -> uuid.UUID:
    raw = submission.get("attempt_id")
    if not isinstance(raw, str):
        raise GradingError(422, "submission requires attempt_id")
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise GradingError(422, "invalid attempt_id") from exc


def optional_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
