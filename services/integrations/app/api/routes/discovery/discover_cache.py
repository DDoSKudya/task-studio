from __future__ import annotations

import uuid

from app.api.routes.common.helpers import (
    filter_summaries,
    platform_block_from_fetch,
    summaries_from_cache,
)
from app.domain.cache import list_cached_courses
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.api.integration_schemas import PlatformCatalogBlock
from studio_integration_sdk.registry import AdapterModule


async def cached_or_error_block(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    platform_id: str,
    adapter: AdapterModule,
    credentials: dict[str, str],
    needle: str,
    ready_message: str,
    error: str,
) -> PlatformCatalogBlock:
    cached = await list_cached_courses(session, user_id=user_id, platform_id=platform_id)
    if cached_courses := filter_summaries(summaries_from_cache(cached), needle=needle):
        block = platform_block_from_fetch(
            adapter,
            credentials=credentials,
            needle=needle,
            remote=[course.model_dump() for course in cached_courses],
        )
        return block.model_copy(
            update={
                "status": "ready",
                "message": ready_message,
            }
        )
    return platform_block_from_fetch(
        adapter,
        credentials=credentials,
        needle=needle,
        error=error,
    )
