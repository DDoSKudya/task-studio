from __future__ import annotations

from app.domain.check.cascade import GradeContext
from app.domain.executable import step_checker_mode
from app.domain.harness.resolve import HarnessBlocked, resolve_harness
from app.domain.check.outcome import CheckOutcome, GradingError


async def stage_local_harness(ctx: GradeContext) -> CheckOutcome | None:
    from app.domain.code import grade as host

    resolved = resolve_harness(ctx.step, ctx.source)
    if resolved is None:
        force_llm = step_checker_mode(ctx.step) == "llm"
        has_tests = isinstance(ctx.step.get("tests"), list) and bool(ctx.step.get("tests"))
        ctx.prior_feedback = (
            "checker=llm"
            if force_llm
            else ("tests not executable locally" if has_tests else "no automated tests")
        )
        ctx.prior_checker = "none"
        ctx.ungradable_feedback = "This step has no automated tests for code grading"
        return None

    if isinstance(resolved, HarnessBlocked):
        ctx.prior_feedback = resolved.reason
        ctx.prior_checker = resolved.checker
        ctx.ungradable_feedback = resolved.ungradable
        return None

    try:
        piston_result = await host.execute_piston_job(
            ctx.client,
            settings=ctx.settings,
            job=resolved.job,
        )
    except GradingError as exc:
        ctx.prior_feedback = exc.detail
        ctx.prior_checker = resolved.checker
        ctx.ungradable_feedback = exc.detail
        return None

                                                            
    return host.piston_outcome(piston_result, started=ctx.started, checker=resolved.checker)
