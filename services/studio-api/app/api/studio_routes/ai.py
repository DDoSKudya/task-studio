from __future__ import annotations

from typing import Annotated

import httpx
from app.api.studio_routes.ai_course import router as course_router
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import parse_upstream
from fastapi import APIRouter, Depends
from studio_contracts.studio_schemas import (
    FetchArticleFromUrlRequest,
    FetchArticleFromUrlResponse,
    FetchArticlesFromUrlsRequest,
    FetchArticlesFromUrlsResponse,
    StudioSuggestRequest,
    StudioSuggestResponse,
)

router = APIRouter(prefix="/v1/studio", tags=["studio"])
router.include_router(course_router)

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.post("/ai/suggest", response_model=StudioSuggestResponse)
async def suggest_manifest(
    body: StudioSuggestRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> StudioSuggestResponse:
    response = await client.post(
        f"{settings.tutor_service_url}/internal/v1/tutor/studio/suggest",
        headers={"X-User-Id": str(user_id)},
        json=body.model_dump(mode="json"),
        timeout=120.0,
    )
    return parse_upstream(response, StudioSuggestResponse)


@router.post("/ai/fetch-article-from-url", response_model=FetchArticleFromUrlResponse)
async def fetch_article_from_url(
    body: FetchArticleFromUrlRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> FetchArticleFromUrlResponse:
    response = await client.post(
        f"{settings.tutor_service_url}/internal/v1/tutor/studio/fetch-article-from-url",
        headers={"X-User-Id": str(user_id)},
        json=body.model_dump(mode="json"),
        timeout=httpx.Timeout(connect=10.0, read=180.0, write=60.0, pool=10.0),
    )
    return parse_upstream(response, FetchArticleFromUrlResponse)


@router.post("/ai/fetch-articles-from-urls", response_model=FetchArticlesFromUrlsResponse)
async def fetch_articles_from_urls(
    body: FetchArticlesFromUrlsRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> FetchArticlesFromUrlsResponse:
    # Sequential upstream fetches — allow long read for multi-URL paste.
    response = await client.post(
        f"{settings.tutor_service_url}/internal/v1/tutor/studio/fetch-articles-from-urls",
        headers={"X-User-Id": str(user_id)},
        json=body.model_dump(mode="json"),
        timeout=httpx.Timeout(connect=10.0, read=900.0, write=60.0, pool=10.0),
    )
    return parse_upstream(response, FetchArticlesFromUrlsResponse)
