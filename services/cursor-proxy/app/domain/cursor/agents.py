from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.domain.cursor.agent_ops import delete_agent, get_run
from app.domain.cursor.http import (
    CursorApiError,
    basic_auth,
    error_detail,
    json_headers,
)

log = structlog.get_logger("cursor-proxy.cursor")

__all__ = [
    "create_chat_run",
    "get_run",
    "delete_agent",
]


async def create_chat_run(
    client: httpx.AsyncClient,
    *,
    api_base: str,
    api_key: str,
    prompt: str,
    model: str | None,
    request_timeout: float = 900.0,
) -> tuple[str, str]:
    body: dict[str, Any] = {
        "prompt": {"text": prompt},
    }
    if model and model.strip().lower() not in {"auto", "default"}:
        body["model"] = {"id": model.strip()}

    try:
        response = await client.post(
            f"{api_base}/v1/agents",
            headers=json_headers(),
            auth=basic_auth(api_key),
            json=body,
            timeout=request_timeout,
        )
    except httpx.TimeoutException as exc:
        raise CursorApiError(
            504,
            "Cursor API timed out while creating the agent. Try again or use Ollama/external.",
        ) from exc
    except httpx.HTTPError as exc:
        raise CursorApiError(502, f"Cursor API unreachable ({exc.__class__.__name__})") from exc

    if response.status_code >= 400:
        detail = error_detail(response)
        log.warning("cursor_create_failed", status=response.status_code, detail=detail[:300])
        raise CursorApiError(response.status_code, detail)
    payload = response.json()
    if not isinstance(payload, dict):
        raise CursorApiError(502, "invalid Cursor create response")
    agent = payload.get("agent")
    run = payload.get("run")
    if not isinstance(agent, dict) or not isinstance(run, dict):
        raise CursorApiError(502, "Cursor create response missing agent/run")
    agent_id = agent.get("id")
    run_id = run.get("id")
    if not isinstance(agent_id, str) or not isinstance(run_id, str):
        raise CursorApiError(502, "Cursor create response missing ids")
    log.info("cursor_run_created", agent_id=agent_id, run_id=run_id)
    return agent_id, run_id
