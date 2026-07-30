from __future__ import annotations

import uuid

import httpx
from app.config import GradingSettings
from app.domain.check.outcome import CheckOutcome
from app.domain.check.task import extract_text_submission, grade_task
from app.domain.code.grade import grade_code
from app.domain.quiz.grade import grade_quiz


def has_choice(submission: dict[str, object]) -> bool:
    choice = submission.get("choice_index")
    if choice is None:
        choice = submission.get("choice")
    return isinstance(choice, int) and not isinstance(choice, bool)


async def infer_unknown_kind(
    step: dict[str, object],
    submission: dict[str, object],
    *,
    settings: GradingSettings,
    client: httpx.AsyncClient,
    user_id: uuid.UUID | None,
) -> CheckOutcome:

    if has_choice(submission):
        return await grade_quiz(
            {**step, "kind": "quiz"},
            submission,
            settings=settings,
            client=client,
            user_id=user_id,
        )
    source = submission.get("source")
    if (
        isinstance(source, str)
        and source.strip()
        and not extract_text_submission({k: v for k, v in submission.items() if k != "source"})
    ):
        return await grade_code(
            {**step, "kind": "code"},
            submission,
            settings=settings,
            client=client,
            user_id=user_id,
        )
    return await grade_task(
        step,
        submission,
        settings=settings,
        client=client,
        user_id=user_id,
        kind="task",
    )
