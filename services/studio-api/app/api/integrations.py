from __future__ import annotations

import uuid
from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream, parse_upstream_list
from fastapi import APIRouter, Depends, Query
from studio_contracts.integration_schemas import (
    AdapterInfo,
    ExternalCourseSummary,
    ImportJobResponse,
    StartImportRequest,
)
from studio_contracts.search_schemas import SearchImportRequest, SearchResponse, SearchType

router = APIRouter(tags=["integrations-search"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.get("/v1/integrations", response_model=list[AdapterInfo])
async def list_integrations(settings: Settings, client: UpstreamClient) -> list[AdapterInfo]:
    upstream = await client.get(f"{settings.integrations_service_url}/internal/v1/integrations")
    return parse_upstream_list(upstream, AdapterInfo)


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


@router.post("/v1/integrations/{platform_id}/import", response_model=ImportJobResponse)
async def start_integration_import(
    platform_id: str,
    body: StartImportRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> ImportJobResponse:
    upstream = await call_service(
        client,
        settings.integrations_service_url,
        "post",
        f"/internal/v1/integrations/{platform_id}/import",
        user_id=user_id,
        json=body.model_dump(mode="json"),
    )
    return parse_upstream(upstream, ImportJobResponse)


@router.get("/v1/integrations/jobs/{job_id}", response_model=ImportJobResponse)
async def get_integration_job(
    job_id: uuid.UUID,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> ImportJobResponse:
    upstream = await call_service(
        client,
        settings.integrations_service_url,
        "get",
        f"/internal/v1/integrations/jobs/{job_id}",
        user_id=user_id,
    )
    return parse_upstream(upstream, ImportJobResponse)


@router.get("/v1/search", response_model=SearchResponse)
async def search(
    q: Annotated[str, Query(min_length=1)],
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
    type: Annotated[SearchType | None, Query(alias="type")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    params: dict[str, str | int] = {"q": q, "limit": limit}
    if type is not None:
        params["type"] = type
    upstream = await call_service(
        client,
        settings.search_service_url,
        "get",
        "/internal/v1/search",
        user_id=user_id,
        params=params,
    )
    return parse_upstream(upstream, SearchResponse)


@router.post("/v1/search/import", response_model=ImportJobResponse)
async def search_import(
    body: SearchImportRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> ImportJobResponse:
    upstream = await call_service(
        client,
        settings.integrations_service_url,
        "post",
        f"/internal/v1/integrations/{body.platform}/import",
        user_id=user_id,
        json={"course_id": body.external_id},
    )
    return parse_upstream(upstream, ImportJobResponse)
