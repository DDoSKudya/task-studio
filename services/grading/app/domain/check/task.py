from __future__ import annotations

import uuid

import httpx
from app.config import GradingSettings
from app.domain.check.cascade import GradeContext, run_chain, stage_llm, stage_ungradable
from app.domain.check.outcome import CheckOutcome


def extract_text_submission(submission: dict[str, object]) -> str:
    for key in ("text", "answer", "report", "notes", "source"):
        value = submission.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


async def grade_task(
    step: dict[str, object],
    submission: dict[str, object],
    *,
    settings: GradingSettings,
    client: httpx.AsyncClient,
    user_id: uuid.UUID | None = None,
    kind: str | None = None,
) -> CheckOutcome:
    text = extract_text_submission(submission)
    if not text:
        return CheckOutcome(
            passed=False,
            score=0.0,
            feedback="Enter an answer before submitting",
            details={"gradable": True, "checker": "none"},
            checker="none",
            duration_ms=0,
        )

    grade_kind = kind if isinstance(kind, str) and kind.strip() else "task"
    ctx = GradeContext(
        step=step,
        submission={**submission, "text": text},
        settings=settings,
        client=client,
        kind=grade_kind if grade_kind in {"task", "lab"} else "task",
        user_id=user_id,
        prior_feedback="open task",
        prior_checker=grade_kind,
        ungradable_feedback="Could not grade the answer (AI grader unavailable)",
    )
    return await run_chain(ctx, (stage_llm, stage_ungradable))
