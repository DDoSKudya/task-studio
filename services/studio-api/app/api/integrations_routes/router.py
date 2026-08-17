from __future__ import annotations

from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream, parse_upstream_list
from fastapi import APIRouter, Depends, Query
from studio_contracts.api.integration_schemas import (
    AdapterInfo,
    DiscoverResponse,
    ExternalCourseSummary,
)

router = APIRouter(tags=["integrations"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.get("/v1/integrations", response_model=list[AdapterInfo])
async def list_integrations(settings: Settings, client: UpstreamClient) -> list[AdapterInfo]:
    upstream = await client.get(f"{settings.integrations_service_url}/internal/v1/integrations")
    return parse_upstream_list(upstream, AdapterInfo)


@router.get("/v1/integrations/discover", response_model=DiscoverResponse)
async def discover_courses(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
    q: Annotated[str | None, Query()] = None,
) -> DiscoverResponse:
    params: dict[str, str | int] = {}
    if q and q.strip():
        params["q"] = q.strip()
    upstream = await call_service(
        client,
        settings.integrations_service_url,
        "get",
        "/internal/v1/integrations/discover",
        user_id=user_id,
        params=params or None,
    )
    return parse_upstream(upstream, DiscoverResponse)


@router.get("/v1/integrations/{platform_id}/catalog", response_model=list[ExternalCourseSummary])
async def integration_catalog(
    platform_id: str,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> list[ExternalCourseSummary]:
    upstream = await call_service(
        client,
        settings.integrations_service_url,
        "get",
        f"/internal/v1/integrations/{platform_id}/catalog",
        user_id=user_id,
    )
    return parse_upstream_list(upstream, ExternalCourseSummary)
