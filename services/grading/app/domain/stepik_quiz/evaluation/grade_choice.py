from __future__ import annotations

import httpx
from app.domain.stepik_quiz.errors import StepikQuizError
from app.domain.stepik_quiz.evaluation.detect import external_step_id_from_step
from app.domain.stepik_quiz.transport.http import (
    _create_attempt,
    _maybe_token,
    _session_headers,
    _submit_reply,
)
from app.domain.stepik_quiz.transport.replies import _norm, _submission_feedback


async def grade_via_stepik(
    client: httpx.AsyncClient,
    *,
    step: dict[str, object],
    choice_index: int,
    credentials: dict[str, str],
) -> tuple[bool, str | None, dict[str, object]]:
    external_id = external_step_id_from_step(step)
    if not external_id:
        raise StepikQuizError("stepik step id missing")

    choices = step.get("choices")
    if not isinstance(choices, list) or choice_index < 0 or choice_index >= len(choices):
        raise StepikQuizError("choice_index out of range")
    selected = choices[choice_index]
    if not isinstance(selected, str) or not selected.strip():
        raise StepikQuizError("selected choice is empty")
    selected_norm = _norm(selected)

    token = await _maybe_token(client, credentials)
    headers = await _session_headers(client, token=token)

    attempt = await _create_attempt(client, headers=headers, external_id=external_id)
    attempt_id = attempt.get("id")
    dataset = attempt.get("dataset") if isinstance(attempt.get("dataset"), dict) else {}
    options = dataset.get("options") if isinstance(dataset, dict) else None
    if not isinstance(attempt_id, int) or not isinstance(options, list) or not options:
        raise StepikQuizError("stepik dataset options missing")

    reply_flags = [_norm(str(option)) == selected_norm for option in options]
    if not any(reply_flags):
        raise StepikQuizError("selected choice not found in stepik dataset")

    submission = await _submit_reply(
        client,
        headers=headers,
        attempt_id=attempt_id,
        reply={"choices": reply_flags},
    )
    status = str(submission.get("status") or "").casefold()
    if status in {"evaluation", "pending", ""}:
        details: dict[str, object] = {
            "checker": "stepik",
            "status": "still_evaluating",
            "actual": choice_index,
            "external_step_id": external_id,
            "gradable": False,
        }
        return False, "evaluation still in progress", details
    passed = status in {"correct", "passed", "ok"}
    feedback = _submission_feedback(submission, fallback=None if passed else "incorrect answer")
    details = {
        "checker": "stepik",
        "status": status,
        "actual": choice_index,
        "external_step_id": external_id,
        "gradable": True,
    }
    score = submission.get("score")
    if isinstance(score, int | float):
        details["stepik_score"] = float(score)
    return passed, feedback, details
