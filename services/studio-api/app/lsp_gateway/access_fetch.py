from __future__ import annotations

import uuid

import httpx
from fastapi import HTTPException, status
from studio_contracts.api.session_schemas import SessionState

from app.config import StudioApiSettings


async def fetch_session(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> SessionState:
    response = await client.get(
        f"{settings.sessions_service_url}/internal/v1/sessions/{session_id}",
        headers={"X-User-Id": str(user_id)},
    )
    if response.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session not found")
    if response.is_error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="sessions unavailable")
    return SessionState.model_validate(response.json())


async def fetch_user_settings(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    user_id: uuid.UUID,
) -> dict[str, object]:
    response = await client.get(
        f"{settings.auth_service_url}/internal/v1/auth/me",
        headers={"X-User-Id": str(user_id)},
    )
    if response.is_error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="auth unavailable")
    payload = response.json()
    if not isinstance(payload, dict):
        return {}
    user_settings = payload.get("settings")
    return user_settings if isinstance(user_settings, dict) else {}
