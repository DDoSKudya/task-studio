from __future__ import annotations

from typing import Annotated

from app.api.analytics_routes.proxy import proxy_analytics
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from fastapi import APIRouter, Depends, Query
from studio_contracts.analytics_schemas import (
    AttemptsTimelineResponse,
    ProgressResponse,
    SkipsResponse,
)

router = APIRouter(prefix="/v1/analytics", tags=["analytics"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.get("/progress", response_model=ProgressResponse)
async def progress(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> ProgressResponse:
    return await proxy_analytics(
        client,
        settings,
        user_id,
        "/internal/v1/analytics/progress",
        ProgressResponse,
        params={"days": days},
    )


@router.get("/skips", response_model=SkipsResponse)
async def skips(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> SkipsResponse:
    return await proxy_analytics(
        client,
        settings,
        user_id,
        "/internal/v1/analytics/skips",
        SkipsResponse,
    )


@router.get("/attempts", response_model=AttemptsTimelineResponse)
async def attempts(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> AttemptsTimelineResponse:
    params: dict[str, str | int] = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await proxy_analytics(
        client,
        settings,
        user_id,
        "/internal/v1/analytics/attempts",
        AttemptsTimelineResponse,
        params=params,
    )
