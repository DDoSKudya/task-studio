from __future__ import annotations

import asyncio
import uuid

from app.api.routes.helpers import (
    fetch_remote_courses,
    filter_summaries,
    platform_block_from_fetch,
    summaries_from_cache,
)
from app.config import IntegrationsSettings
from app.domain.cache import list_cached_courses, replace_external_courses, upsert_external_courses
from app.domain.messaging import publish_external_courses_for_index
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.integration_schemas import PlatformCatalogBlock
from studio_integration_sdk.registry import AdapterModule


async def fetch_and_sync_platform_block(
    *,
    session: AsyncSession,
    settings: IntegrationsSettings,
    user_id: uuid.UUID,
    platform_id: str,
    adapter: AdapterModule,
    credentials: dict[str, str],
    needle: str,
) -> PlatformCatalogBlock:
    remote = await asyncio.to_thread(
        fetch_remote_courses, adapter, credentials=credentials, needle=needle
    )
    block = platform_block_from_fetch(
        adapter,
        credentials=credentials,
        needle=needle,
        remote=remote,
    )
    if needle:
        if remote:
            await upsert_external_courses(
                session,
                user_id=user_id,
                platform_id=platform_id,
                courses=remote,
            )
    elif remote:
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
    else:
        cached = await list_cached_courses(session, user_id=user_id, platform_id=platform_id)
        if cached_courses := filter_summaries(summaries_from_cache(cached), needle=needle):
            block = platform_block_from_fetch(
                adapter,
                credentials=credentials,
                needle=needle,
                remote=[course.model_dump() for course in cached_courses],
            )
            block = block.model_copy(
                update={
                    "status": "ready",
                    "message": "cached catalog (upstream empty)",
                }
            )
    return block
