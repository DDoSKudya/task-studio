from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from app.domain.stepik_quiz.constants import _API


async def _wait_for_verdict(
    client: httpx.AsyncClient,
    *,
    headers: dict[str, str],
    submission: dict[str, Any],
    timeout_seconds: float = 12.0,
) -> dict[str, Any]:
    status = str(submission.get("status") or "").casefold()
    if status and status not in {"evaluation", "pending", ""}:
        return submission
    submission_id = submission.get("id")
    if not isinstance(submission_id, int):
        return submission
    deadline = time.monotonic() + timeout_seconds
    current = submission
    while time.monotonic() < deadline:
        await asyncio.sleep(0.45)
        try:
            response = await client.get(
                f"{_API}/submissions/{submission_id}",
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            rows = response.json().get("submissions") or []
        except (httpx.HTTPError, ValueError, TypeError):
            break
        if rows and isinstance(rows[0], dict):
            current = rows[0]
            status = str(current.get("status") or "").casefold()
            if status and status not in {"evaluation", "pending"}:
                return current
    return current
