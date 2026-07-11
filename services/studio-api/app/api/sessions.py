from __future__ import annotations

import uuid
from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream, parse_upstream_list
from fastapi import APIRouter, Depends, status
from studio_contracts.session_schemas import (
    AttemptInfo,
    NavigateRequest,
    SessionState,
    SessionSummary,
    StartSessionRequest,
    StepContent,
    SubmitRequest,
    SubmitResult,
)

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.get("", response_model=list[SessionSummary])
async def list_sessions(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> list[SessionSummary]:
    upstream = await call_service(
        client,
        settings.sessions_service_url,
        "get",
        "/internal/v1/sessions",
        user_id=user_id,
    )
    return parse_upstream_list(upstream, SessionSummary)


@router.post("", response_model=SessionState, status_code=status.HTTP_201_CREATED)
async def start_session(
    body: StartSessionRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> SessionState:
    upstream = await call_service(
        client,
        settings.sessions_service_url,
        "post",
        "/internal/v1/sessions",
        user_id=user_id,
        json=body.model_dump(mode="json"),
    )
    return parse_upstream(upstream, SessionState)


@router.get("/{session_id}", response_model=SessionState)
async def get_session(
    session_id: uuid.UUID,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> SessionState:
    upstream = await call_service(
        client,
        settings.sessions_service_url,
        "get",
        f"/internal/v1/sessions/{session_id}",
        user_id=user_id,
    )
    return parse_upstream(upstream, SessionState)


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


@router.post("/{session_id}/submit", response_model=SubmitResult)
async def submit(
    session_id: uuid.UUID,
    body: SubmitRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> SubmitResult:
    upstream = await call_service(
        client,
        settings.sessions_service_url,
        "post",
        f"/internal/v1/sessions/{session_id}/submit",
        user_id=user_id,
        json=body.model_dump(mode="json"),
    )
    return parse_upstream(upstream, SubmitResult)


@router.get("/{session_id}/attempts", response_model=list[AttemptInfo])
async def list_attempts(
    session_id: uuid.UUID,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> list[AttemptInfo]:
    upstream = await call_service(
        client,
        settings.sessions_service_url,
        "get",
        f"/internal/v1/sessions/{session_id}/attempts",
        user_id=user_id,
    )
    return parse_upstream_list(upstream, AttemptInfo)
