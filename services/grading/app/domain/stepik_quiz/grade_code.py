from __future__ import annotations

from typing import Any

import httpx

from .detect import external_step_id_from_step
from .errors import StepikQuizError
from .http import _create_attempt, _maybe_token, _session_headers, _submit_reply
from .replies import _code_reply_candidates, _submission_feedback


async def grade_code_via_stepik(
    client: httpx.AsyncClient,
    *,
    step: dict[str, object],
    source: str,
    credentials: dict[str, str],
) -> tuple[bool, str | None, dict[str, object]]:
    external_id = external_step_id_from_step(step)
    if not external_id:
        raise StepikQuizError("stepik step id missing")
    if not source.strip():
        raise StepikQuizError("empty source")

    token = await _maybe_token(client, credentials)
    headers = await _session_headers(client, token=token)
    attempt = await _create_attempt(client, headers=headers, external_id=external_id)
    attempt_id = attempt.get("id")
    if not isinstance(attempt_id, int):
        raise StepikQuizError("stepik attempt response invalid")

    last_error: str | None = None
    submission: dict[str, Any] | None = None

    for reply in _code_reply_candidates(step, source, attempt):
        try:
            submission = await _submit_reply(
                client,
                headers=headers,
                attempt_id=attempt_id,
                reply=reply,
                timeout_seconds=25.0,
            )
            break
        except StepikQuizError as exc:
            last_error = exc.detail

            attempt = await _create_attempt(client, headers=headers, external_id=external_id)
            attempt_id = attempt.get("id")
            if not isinstance(attempt_id, int):
                raise StepikQuizError("stepik attempt response invalid") from exc

    if submission is None:
        raise StepikQuizError(last_error or "stepik code submission failed")

    status = str(submission.get("status") or "").casefold()
    if status in {"evaluation", "pending", ""}:
        details: dict[str, object] = {
            "checker": "stepik",
            "status": "still_evaluating",
            "external_step_id": external_id,
            "gradable": False,
        }
        return False, "evaluation still in progress", details
    passed = status in {"correct", "passed", "ok"}
    feedback = _submission_feedback(
        submission,
        fallback=None if passed else "incorrect solution",
    )
    details = {
        "checker": "stepik",
        "status": status,
        "external_step_id": external_id,
        "gradable": True,
    }
    score = submission.get("score")
    if isinstance(score, int | float):
        details["stepik_score"] = float(score)
    hint = submission.get("hint")
    if isinstance(hint, str) and hint.strip():
        details["hint"] = hint.strip()
    return passed, feedback, details
