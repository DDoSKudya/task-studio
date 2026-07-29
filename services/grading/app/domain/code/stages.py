from __future__ import annotations

from app.domain.check.cascade import GradeContext
from app.domain.code.harness import stage_local_harness
from app.domain.code.stepik import stage_stepik
from app.domain.check.outcome import CheckOutcome

__all__ = [
    "stage_require_source",
    "stage_stepik",
    "stage_local_harness",
]


async def stage_require_source(ctx: GradeContext) -> CheckOutcome | None:
    source = ctx.submission.get("source")
    if not isinstance(source, str) or not source.strip():
        return CheckOutcome(
            passed=False,
            score=0.0,
            feedback="Paste your solution code before submitting",
            details={"gradable": True, "checker": "none"},
            checker="none",
            duration_ms=0,
        )
    ctx.source = source
    return None
