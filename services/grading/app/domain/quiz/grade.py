                                                           

from __future__ import annotations

import uuid
from dataclasses import replace

import httpx
from app.config import GradingSettings
from app.domain.check.cascade import GradeContext, run_chain, stage_llm, stage_ungradable
from app.domain.check.outcome import CheckOutcome, GradingError
from app.domain.quiz.stages import quiz_answer_index, stage_answer_key, stage_stepik
from app.domain.stepik_quiz import (
    StepikQuizError,
    fetch_stepik_credentials,
    grade_via_stepik,
    is_stepik_quiz,
)

                                                                               
_stage_answer_key = stage_answer_key
_stage_stepik = stage_stepik

__all__ = [
    "grade_quiz",
    "StepikQuizError",
    "fetch_stepik_credentials",
    "grade_via_stepik",
    "is_stepik_quiz",
]


async def grade_quiz(
    step: dict[str, object],
    submission: dict[str, object],
    *,
    settings: GradingSettings,
    client: httpx.AsyncClient,
    user_id: uuid.UUID | None = None,
) -> CheckOutcome:
    choice = submission.get("choice_index")
    if choice is None:
        choice = submission.get("choice")
    if not isinstance(choice, int) or isinstance(choice, bool):
        raise GradingError(422, "quiz submission requires choice_index")

    ctx = GradeContext(
        step=step,
        submission=submission,
        settings=settings,
        client=client,
        kind="quiz",
        user_id=user_id,
        prior_feedback="answer key unavailable",
        prior_checker="quiz",
        ungradable_feedback="answer key unavailable",
    )
                                                                 
    ctx.submission = {**submission, "choice_index": choice}

    return _with_quiz_reveal(
        step,
        await run_chain(
            ctx,
            (
                _stage_answer_key,
                _stage_stepik,
                stage_llm,
                stage_ungradable,
            ),
        ),
    )


def _with_quiz_reveal(step: dict[str, object], outcome: CheckOutcome) -> CheckOutcome:
                                                                                      
    if outcome.passed:
        return outcome
    if outcome.details.get("expected") is not None:
        return outcome
    answer = quiz_answer_index(step)
    if answer is None:
        return outcome
    details = dict(outcome.details)
    details["expected"] = answer
    return replace(outcome, details=details)
