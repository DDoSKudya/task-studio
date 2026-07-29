from __future__ import annotations

import httpx

from app.domain.cursor.agents import create_chat_run, delete_agent, get_run
from app.domain.cursor.http import (
    CursorApiError,
    basic_auth,
    error_detail,
    json_headers,
    model_ids_from_payload,
)

                                                          
from .run_poll import (  # noqa: E402
    _result_text_from_payload,
    _run_status,
    wait_for_run_result,
)

__all__ = [
    "CursorApiError",
    "create_chat_run",
    "delete_agent",
    "get_run",
    "list_models",
    "wait_for_run_result",
    "_run_status",
    "_result_text_from_payload",
]


async def list_models(
    client: httpx.AsyncClient,
    *,
    api_base: str,
    api_key: str,
) -> list[str]:
    response = await client.get(
        f"{api_base}/v1/models",
        headers=json_headers(),
        auth=basic_auth(api_key),
        timeout=30.0,
    )
    if response.status_code >= 400:
        raise CursorApiError(response.status_code, error_detail(response))
    return model_ids_from_payload(response.json())
