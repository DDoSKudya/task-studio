from __future__ import annotations

import asyncio

import httpx

from .client import CursorApiError, get_run
from .run_status import (
    TERMINAL_STATUSES,
    is_terminal_ok,
    result_text_from_payload,
    run_status,
)

_run_status = run_status
_result_text_from_payload = result_text_from_payload


async def wait_for_run_result(
    client: httpx.AsyncClient,
    *,
    api_base: str,
    api_key: str,
    agent_id: str,
    run_id: str,
    request_timeout: float,
    poll_interval: float = 1.0,
) -> str:
    deadline = asyncio.get_running_loop().time() + max(5.0, request_timeout)
    last_status = ""
    while asyncio.get_running_loop().time() < deadline:
        payload = await get_run(
            client,
            api_base=api_base,
            api_key=api_key,
            agent_id=agent_id,
            run_id=run_id,
        )
        if payload is None:
            await asyncio.sleep(poll_interval)
            continue
        status = run_status(payload)
        last_status = status or last_status
        if status in TERMINAL_STATUSES:
            if text := result_text_from_payload(payload):
                return text
            if is_terminal_ok(status):
                raise CursorApiError(502, "Cursor run finished with empty result")
            raise CursorApiError(
                502,
                f"Cursor run ended with status {status or 'UNKNOWN'}",
            )
        await asyncio.sleep(poll_interval)

    raise CursorApiError(
        504,
        f"Cursor run timed out after {int(request_timeout)}s"
        + (f" (last status: {last_status})" if last_status else ""),
    )
