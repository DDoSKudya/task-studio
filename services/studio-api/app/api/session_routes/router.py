from __future__ import annotations

import uuid
from typing import Annotated

from app.api.session_routes.attempts import router as attempts_router
from app.api.session_routes.study import router as study_router
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream, parse_upstream_list
from fastapi import APIRouter, Depends
from studio_contracts.api.session_schemas import (
    PackProgressItem,
    SessionState,
    SessionSummary,
    StartSessionRequest,
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


@router.get("/pack-progress", response_model=list[PackProgressItem])
async def list_pack_progress(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> list[PackProgressItem]:
    upstream = await call_service(
        client,
        settings.sessions_service_url,
        "get",
        "/internal/v1/sessions/pack-progress",
        user_id=user_id,
    )
    return parse_upstream_list(upstream, PackProgressItem)


@router.post("", response_model=SessionState)
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


router.include_router(study_router)
router.include_router(attempts_router)
