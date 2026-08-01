from __future__ import annotations

import time

from app.domain.check.cascade import GradeContext
from app.domain.check.outcome import CheckOutcome, GradingError
from app.domain.stepik_quiz import is_stepik_quiz


def quiz_answer_index(step: dict[str, object]) -> int | None:
    raw = step.get("answer")
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return None


async def stage_answer_key(ctx: GradeContext) -> CheckOutcome | None:
    answer = quiz_answer_index(ctx.step)
    if answer is None:
        return None
    choice = ctx.submission.get("choice_index")
    if not isinstance(choice, int) or isinstance(choice, bool):
        raise GradingError(422, "quiz submission requires choice_index")
    passed = choice == answer
    return CheckOutcome(
        passed=passed,
        score=1.0 if passed else 0.0,
        feedback=None if passed else "incorrect answer",
        details={"expected": answer, "actual": choice, "gradable": True},
        checker="quiz",
        duration_ms=0,
    )


async def stage_stepik(ctx: GradeContext) -> CheckOutcome | None:
    from app.domain import quiz_grade as host

    if not is_stepik_quiz(ctx.step):
        return None
    choice = ctx.submission.get("choice_index")
    if not isinstance(choice, int) or isinstance(choice, bool):
        raise GradingError(422, "quiz submission requires choice_index")
    credentials = await host.fetch_stepik_credentials(
        ctx.client,
        auth_service_url=ctx.settings.auth_service_url,
        user_id=ctx.user_id,
    )
    try:
        passed, feedback, details = await host.grade_via_stepik(
            ctx.client,
            step=ctx.step,
            choice_index=choice,
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
