from __future__ import annotations

import time

from app.domain.check.cascade import GradeContext
from app.domain.check.outcome import CheckOutcome
from app.domain.sql.grade import has_local_test_artifacts
from app.domain.stepik_quiz import is_stepik_quiz


async def stage_stepik(ctx: GradeContext) -> CheckOutcome | None:
    from app.domain.code import grade as host

    if has_local_test_artifacts(ctx.step):
        return None
    if not is_stepik_quiz(ctx.step):
        return None

    credentials = await host.fetch_stepik_credentials(
        ctx.client,
        auth_service_url=ctx.settings.auth_service_url,
        user_id=ctx.user_id,
    )
    try:
        passed, feedback, details = await host.grade_code_via_stepik(
            ctx.client,
            step=ctx.step,
            source=ctx.source,
            credentials=credentials,
        )
    except host.StepikQuizError as exc:
        ctx.prior_feedback = exc.detail
        ctx.prior_checker = "stepik"
        ctx.ungradable_feedback = exc.detail
        return None

    return CheckOutcome(
        passed=passed,
        score=1.0 if passed else 0.0,
        feedback=feedback,
        details=details,
        checker="stepik",
        duration_ms=int((time.perf_counter() - ctx.started) * 1000),
    )
