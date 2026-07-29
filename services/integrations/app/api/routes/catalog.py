from __future__ import annotations

import asyncio
from typing import Annotated

import httpx
from app.api.deps import Adapters, DbSession, Settings
from app.api.routes.helpers import http_client, require_adapter, summaries_from_cache
from app.domain.cache import list_cached_courses, replace_external_courses
from app.domain.credentials import fetch_platform_credentials
from app.domain.messaging import publish_external_courses_for_index
from fastapi import APIRouter, Depends
from studio_common.internal import InternalUserId
from studio_contracts.integration_schemas import ExternalCourseSummary

router = APIRouter()

type HttpClient = Annotated[httpx.AsyncClient, Depends(http_client)]


@router.get("/{platform_id}/catalog", response_model=list[ExternalCourseSummary])
async def platform_catalog(
    platform_id: str,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
    adapters: Adapters,
    client: HttpClient,
) -> list[ExternalCourseSummary]:
    adapter = require_adapter(adapters, platform_id)
    credentials = await fetch_platform_credentials(
        client,
        auth_service_url=settings.auth_service_url,
        user_id=user_id,
        platform_id=platform_id,
    )
    try:
        remote = await asyncio.to_thread(
            adapter.list_catalog,
            user_id=str(user_id),
            **credentials,
        )
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, httpx.HTTPError):
        cached = await list_cached_courses(session, user_id=user_id, platform_id=platform_id)
        return summaries_from_cache(cached)

    if remote:
        await replace_external_courses(
            session,
            user_id=user_id,
            platform_id=platform_id,
            courses=remote,
        )
        await publish_external_courses_for_index(
            settings,
            user_id=user_id,
            platform_id=platform_id,
            courses=remote,
        )
    cached = await list_cached_courses(session, user_id=user_id, platform_id=platform_id)
    return summaries_from_cache(cached)
