from __future__ import annotations

from contextlib import suppress

import httpx
from app.domain.stepik_quiz.constants import _STEPIK_ORIGIN, _TOKEN_URL


async def _session_headers(
    client: httpx.AsyncClient,
    *,
    token: str | None,
) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": f"{_STEPIK_ORIGIN}/",
        "Origin": _STEPIK_ORIGIN,
        "User-Agent": "task-studio-grading/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        return headers
    with suppress(httpx.HTTPError):
        await client.get(_STEPIK_ORIGIN + "/", headers={"Accept": "text/html"}, timeout=15)
    if csrf := client.cookies.get("csrftoken"):
        headers["X-CSRFToken"] = csrf
    return headers


async def _maybe_token(client: httpx.AsyncClient, credentials: dict[str, str]) -> str | None:
    user = credentials.get("username", "").strip()
    password = credentials.get("password", "").strip()
    client_id = credentials.get("client_id", "").strip()
    client_secret = credentials.get("client_secret", "").strip()
    if not (user and password and client_id and client_secret):
        return None
    try:
        response = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "password",
                "username": user,
                "password": password,
            },
            auth=(client_id, client_secret),
            timeout=20,
        )
        if response.status_code >= 400:
            return None
        token = response.json().get("access_token")
        return token if isinstance(token, str) and token else None
    except (httpx.HTTPError, ValueError, TypeError):
        return None
