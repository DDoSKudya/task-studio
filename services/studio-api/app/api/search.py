from __future__ import annotations

from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream
from fastapi import APIRouter, Depends, Query
from studio_contracts.api.integration_schemas import ImportJobResponse
from studio_contracts.api.search_schemas import SearchImportRequest, SearchResponse, SearchType

router = APIRouter(tags=["search"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


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
        json={"course_id": body.external_id, "force": body.force},
    )
    return parse_upstream(upstream, ImportJobResponse)
