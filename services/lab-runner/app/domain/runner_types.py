from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LabRunOutcome:
    passed: bool
    score: float
    feedback: str | None
    details: dict[str, object]
    duration_ms: int


def elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def failed_outcome(message: str, started: float) -> LabRunOutcome:
    return LabRunOutcome(
        passed=False,
        score=0.0,
        feedback=message,
        details={"error": message},
        duration_ms=elapsed_ms(started),
    )
