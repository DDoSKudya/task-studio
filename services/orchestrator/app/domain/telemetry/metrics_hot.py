from __future__ import annotations

import httpx


async def prometheus_query_matches(
    client: httpx.AsyncClient,
    prometheus_url: str,
    query: str,
) -> bool:
    try:
        response = await client.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": query},
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return False
    body = response.json()
    if not isinstance(body, dict):
        return False
    data = body.get("data")
    if not isinstance(data, dict):
        return False
    result = data.get("result")
    return isinstance(result, list) and bool(result)


async def pyroscope_grading_hot(client: httpx.AsyncClient, pyroscope_url: str) -> bool:
    try:
        response = await client.get(
            f"{pyroscope_url}/api/render",
            params={"query": "grading.cpu", "from": "now-5m", "until": "now"},
            timeout=10.0,
        )
        if response.status_code in {404, 503}:
            return False
        response.raise_for_status()
    except httpx.HTTPError:
        return False
    body = response.json()
    if not isinstance(body, dict):
        return False
    flamebearer = body.get("flamebearer")
    if not isinstance(flamebearer, dict):
        return False
    levels = flamebearer.get("levels")
    return isinstance(levels, list) and bool(levels)
