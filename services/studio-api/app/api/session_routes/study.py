from __future__ import annotations

import uuid
from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream
from fastapi import APIRouter, Depends
from studio_contracts.api.session_schemas import (
    NavigateRequest,
    SessionState,
    StepContent,
)

router = APIRouter()

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.get("/{session_id}/step", response_model=StepContent)
async def get_step(
    session_id: uuid.UUID,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> StepContent:
    upstream = await call_service(
        client,
        settings.sessions_service_url,
        "get",
        f"/internal/v1/sessions/{session_id}/step",
        user_id=user_id,
    )
    return parse_upstream(upstream, StepContent)


@router.post("/{session_id}/navigate", response_model=SessionState)
async def navigate(
    session_id: uuid.UUID,
    body: NavigateRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> SessionState:
    upstream = await call_service(
        client,
        settings.sessions_service_url,
        "post",
        f"/internal/v1/sessions/{session_id}/navigate",
        user_id=user_id,
        json=body.model_dump(mode="json"),
    )
    return parse_upstream(upstream, SessionState)


@router.post("/{session_id}/skip-study", response_model=SessionState)
async def skip_study(
    session_id: uuid.UUID,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> SessionState:
    upstream = await call_service(
        client,
        settings.sessions_service_url,
        "post",
        f"/internal/v1/sessions/{session_id}/skip-study",
        user_id=user_id,
    )
    return parse_upstream(upstream, SessionState)
