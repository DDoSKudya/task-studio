from __future__ import annotations

from typing import Any

import httpx
from app.domain.stepik_quiz.access.auth import _maybe_token, _session_headers
from app.domain.stepik_quiz.constants import _API
from app.domain.stepik_quiz.errors import StepikQuizError
from app.domain.stepik_quiz.transport.http_errors import http_error_detail
from app.domain.stepik_quiz.transport.poll import _wait_for_verdict

__all__ = [
    "_create_attempt",
    "_submit_reply",
    "_http_error_detail",
    "_session_headers",
    "_maybe_token",
    "_wait_for_verdict",
]

_http_error_detail = http_error_detail


async def _create_attempt(
    client: httpx.AsyncClient,
    *,
    headers: dict[str, str],
    external_id: str,
) -> dict[str, Any]:
    attempt_resp = await client.post(
        f"{_API}/attempts",
        headers=headers,
        json={"attempt": {"step": int(external_id)}},
        timeout=30,
    )
    if attempt_resp.status_code >= 400:
        raise StepikQuizError(f"stepik attempt failed ({attempt_resp.status_code})")
    attempts = attempt_resp.json().get("attempts") or []
    if not attempts or not isinstance(attempts[0], dict):
        raise StepikQuizError("stepik attempt response invalid")
    return attempts[0]


async def _submit_reply(
    client: httpx.AsyncClient,
    *,
    headers: dict[str, str],
    attempt_id: int,
    reply: dict[str, Any],
    timeout_seconds: float = 12.0,
) -> dict[str, Any]:
    submit_resp = await client.post(
        f"{_API}/submissions",
        headers=headers,
        json={"submission": {"attempt": attempt_id, "reply": reply}},
        timeout=30,
    )
    if submit_resp.status_code >= 400:
        detail = http_error_detail(submit_resp)
        raise StepikQuizError(detail or f"stepik submission failed ({submit_resp.status_code})")
    submissions = submit_resp.json().get("submissions") or []
    if not submissions or not isinstance(submissions[0], dict):
        raise StepikQuizError("stepik submission response invalid")
    return await _wait_for_verdict(
        client,
        headers=headers,
        submission=submissions[0],
        timeout_seconds=timeout_seconds,
    )
