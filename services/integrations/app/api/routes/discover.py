from __future__ import annotations

from typing import Annotated

import httpx
from app.api.deps import Adapters, DbSession, Settings
from app.api.routes.discover_platform import discover_platform_block
from app.api.routes.helpers import filter_summaries, http_client, summaries_from_cache
from app.domain.cache import list_cached_courses
from fastapi import APIRouter, Depends
from studio_common.internal import InternalUserId
from studio_contracts.integration_schemas import (
    DiscoverResponse,
    ExternalCourseSummary,
    PlatformCatalogBlock,
)

router = APIRouter()

type HttpClient = Annotated[httpx.AsyncClient, Depends(http_client)]


@router.get("/discover", response_model=DiscoverResponse)
async def discover_courses(
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
    adapters: Adapters,
    client: HttpClient,
    q: str | None = None,
) -> DiscoverResponse:
    needle = (q or "").strip()
    platform_blocks: list[PlatformCatalogBlock] = []
    merged: list[ExternalCourseSummary] = []

    for platform_id, adapter in sorted(adapters.items(), key=lambda item: item[0]):
        block = await discover_platform_block(
            session=session,
            settings=settings,
            client=client,
            user_id=user_id,
            platform_id=platform_id,
            adapter=adapter,
            needle=needle,
        )
        if block is None:
            continue
        platform_blocks.append(block)
        merged.extend(block.courses)

    if not merged:
        cached = await list_cached_courses(session, user_id=user_id, platform_id=None)
        merged = filter_summaries(summaries_from_cache(cached), needle=needle)

    deduped: dict[str, ExternalCourseSummary] = {}
    for course in merged:
        deduped[f"{course.platform}:{course.external_id}"] = course

    courses = sorted(deduped.values(), key=lambda item: item.title.casefold())
    return DiscoverResponse(platforms=platform_blocks, courses=courses)
