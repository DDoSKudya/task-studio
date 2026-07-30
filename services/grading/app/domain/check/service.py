                                                                               

from __future__ import annotations

import uuid

import httpx
from app.config import GradingSettings
from app.domain.check.infer import infer_unknown_kind
from app.domain.check.outcome import CheckOutcome, GradingError, parse_attempt_id
from app.domain.check.task import grade_task
from app.domain.code.grade import grade_code
from app.domain.quiz.grade import grade_quiz

__all__ = [
    "CheckOutcome",
    "GradingError",
    "check_submission",
    "grade_code",
    "grade_quiz",
    "grade_task",
    "parse_attempt_id",
]


async def check_submission(
    step: dict[str, object],
    submission: dict[str, object],
    *,
    settings: GradingSettings,
    client: httpx.AsyncClient,
    user_id: uuid.UUID | None = None,
) -> CheckOutcome:
    kind = step.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        kind = "task"
    kind = kind.strip().lower()

    if kind == "quiz":
        return await grade_quiz(step, submission, settings=settings, client=client, user_id=user_id)
    if kind == "code":
        return await grade_code(step, submission, settings=settings, client=client, user_id=user_id)
    if kind in {"task", "lab"}:
        return await grade_task(
            step,
            submission,
            settings=settings,
            client=client,
            user_id=user_id,
            kind=kind,
        )

    return await infer_unknown_kind(
        step,
        submission,
        settings=settings,
        client=client,
        user_id=user_id,
    )
