from __future__ import annotations

import uuid

import httpx
from app.config import TutorConfig
from app.domain.errors import TutorError
from fastapi import status
from pydantic import BaseModel
from studio_common.auth_schemas import MeResponse
from studio_contracts.session_schemas import SessionState, StepContent
from studio_contracts.tutor_schemas import TutorSettings, parse_tutor_settings

_SESSIONS_UNAVAILABLE = "sessions unavailable"
_SESSION_NOT_FOUND = "session not found"


async def _fetch_upstream[T: BaseModel](
    client: httpx.AsyncClient,
    base_url: str,
    path: str,
    *,
    user_id: uuid.UUID,
    model: type[T],
    not_found_detail: str = _SESSION_NOT_FOUND,
    unavailable_detail: str = _SESSIONS_UNAVAILABLE,
) -> T:
    response = await client.get(
        f"{base_url}{path}",
        headers={"X-User-Id": str(user_id)},
    )
    if response.status_code == status.HTTP_404_NOT_FOUND:
        raise TutorError(status.HTTP_404_NOT_FOUND, not_found_detail)
    if response.is_error:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, unavailable_detail)
    return model.model_validate(response.json())


async def fetch_session(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> SessionState:
    return await _fetch_upstream(
        client,
        config.sessions_service_url,
        f"/internal/v1/sessions/{session_id}",
        user_id=user_id,
        model=SessionState,
    )


async def fetch_step(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
) -> StepContent:
    return await _fetch_upstream(
        client,
        config.sessions_service_url,
        f"/internal/v1/sessions/{session_id}/step",
        user_id=user_id,
        model=StepContent,
    )


async def fetch_user_settings(
    client: httpx.AsyncClient,
    config: TutorConfig,
    user_id: uuid.UUID,
) -> TutorSettings:
    response = await client.get(
        f"{config.auth_service_url}/internal/v1/auth/me",
        headers={"X-User-Id": str(user_id)},
    )
    if response.is_error:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "auth unavailable")
    profile = MeResponse.model_validate(response.json())
    return parse_tutor_settings(profile.settings)
