from __future__ import annotations

import re
import time

from app.domain.check.cascade import GradeContext
from app.domain.check.outcome import CheckOutcome, GradingError
from app.domain.piston.client import execute_piston
from app.domain.sql.local import build_sql_seed, looks_like_sql_step


def has_local_test_artifacts(step: dict[str, object]) -> bool:
    tests = step.get("tests")
    if isinstance(tests, list) and bool(tests):
        return True
    test_source = step.get("test_source")
    if isinstance(test_source, str) and bool(test_source.strip()):
        return True
    fcc_tests = step.get("fcc_tests")
    return isinstance(fcc_tests, list) and bool(fcc_tests)


async def stage_sql_local(ctx: GradeContext) -> CheckOutcome | None:
    if has_local_test_artifacts(ctx.step):
        return None
    if not looks_like_sql_step(ctx.step):
        return None
    seed = build_sql_seed(ctx.step)
    if not seed:
        return None
    query = ctx.source.strip().rstrip(";")
    if not query:
        return None
    script = f"{seed}\n{query};"
    try:
        piston_result = await execute_piston(
            ctx.client,
            settings=ctx.settings,
            language="sql",
            version="*",
            source=script,
        )
    except GradingError as exc:
        ctx.prior_feedback = exc.detail
        ctx.prior_checker = "sql_local"
        ctx.ungradable_feedback = exc.detail
        return None

    passed = bool(piston_result["passed"])
    stdout = str(piston_result.get("stdout") or "")
    stderr = str(piston_result.get("stderr") or "")
    if passed and _looks_like_select(query) and not stdout.strip():
        passed = False
        stderr = stderr or "query returned no rows"

    if passed:
        feedback: str | None = "Local check against seed data from the step"
    else:
        feedback = stderr.strip() or "incorrect SQL"

    details: dict[str, object] = {
        **piston_result,
        "checker": "sql_local",
        "gradable": True,
        "offline_fallback": True,
    }
    if ctx.prior_feedback and ctx.prior_checker == "stepik":
        details["stepik_error"] = ctx.prior_feedback

    return CheckOutcome(
        passed=passed,
        score=1.0 if passed else 0.0,
        feedback=feedback,
        details=details,
        checker="sql_local",
        duration_ms=int((time.perf_counter() - ctx.started) * 1000),
    )


def _looks_like_select(query: str) -> bool:
    return bool(re.match(r"^\s*select\b", query, flags=re.IGNORECASE))
