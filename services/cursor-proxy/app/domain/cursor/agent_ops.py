from __future__ import annotations

from typing import Any

import httpx

from app.domain.cursor.http import basic_auth, json_headers


async def get_run(
    client: httpx.AsyncClient,
    *,
    api_base: str,
    api_key: str,
    agent_id: str,
    run_id: str,
) -> dict[str, Any] | None:
    try:
        response = await client.get(
            f"{api_base}/v1/agents/{agent_id}/runs/{run_id}",
            headers=json_headers(),
            auth=basic_auth(api_key),
            timeout=30.0,
        )
    except httpx.HTTPError:
        return None
    if response.status_code >= 400:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


async def delete_agent(
    client: httpx.AsyncClient,
    *,
    api_base: str,
    api_key: str,
    agent_id: str,
) -> None:
    try:
        await client.delete(
            f"{api_base}/v1/agents/{agent_id}",
            headers=json_headers(),
            auth=basic_auth(api_key),
            timeout=15.0,
        )
    except httpx.HTTPError:
        return
