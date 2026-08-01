from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

import httpx
from app.config import GradingSettings
from app.domain.check.outcome import CheckOutcome


@dataclass(slots=True)
class GradeContext:
    step: dict[str, object]
    submission: dict[str, object]
    settings: GradingSettings
    client: httpx.AsyncClient
    kind: str
    user_id: uuid.UUID | None = None
    started: float = field(default_factory=time.perf_counter)
    source: str = ""
    prior_feedback: str | None = None
    prior_checker: str | None = None
    ungradable_feedback: str = "grading unavailable"


GradeStage = Callable[[GradeContext], Awaitable[CheckOutcome | None]]


async def run_chain(ctx: GradeContext, stages: Sequence[GradeStage]) -> CheckOutcome:
    for stage in stages:
        outcome = await stage(ctx)
        if outcome is not None:
            return outcome
    return await stage_ungradable(ctx)


async def stage_llm(ctx: GradeContext) -> CheckOutcome | None:
    from app.domain.llm.grade import try_llm_grade

    return await try_llm_grade(
        ctx.client,
        ctx.settings,
        step=ctx.step,
        submission=ctx.submission,
        kind=ctx.kind,
        user_id=ctx.user_id,
        started=ctx.started,
        prior_feedback=ctx.prior_feedback,
        prior_checker=ctx.prior_checker,
    )


async def stage_ungradable(ctx: GradeContext) -> CheckOutcome:
    elapsed = int((time.perf_counter() - ctx.started) * 1000)
    return CheckOutcome(
        passed=False,
        score=0.0,
        feedback=ctx.ungradable_feedback,
        details={
            "gradable": False,
            "checker": ctx.prior_checker or "none",
            "prior_feedback": ctx.prior_feedback,
        },
        checker=ctx.prior_checker or "none",
        duration_ms=elapsed,
    )
