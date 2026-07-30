from __future__ import annotations

import uuid
from typing import Annotated

import httpx
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream, parse_upstream_list
from fastapi import APIRouter, Depends
from studio_contracts.session_schemas import AttemptInfo, SubmitRequest, SubmitResult

router = APIRouter()

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


_SUBMIT_TIMEOUT = httpx.Timeout(connect=10.0, read=600.0, write=120.0, pool=10.0)


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
        request_timeout=_SUBMIT_TIMEOUT,
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
