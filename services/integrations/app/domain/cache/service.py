from __future__ import annotations

import uuid

from app.domain.cache.parse import parse_catalog_course
from app.domain.cache.upsert import upsert_external_courses
from app.infra.models import ExternalCourseCache
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = [
    "parse_catalog_course",
    "upsert_external_courses",
    "replace_external_courses",
    "list_cached_courses",
]


async def replace_external_courses(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    platform_id: str,
    courses: list[dict[str, object]],
) -> None:
                                                                                 
    await session.execute(
        delete(ExternalCourseCache).where(
            ExternalCourseCache.user_id == user_id,
            ExternalCourseCache.platform_id == platform_id,
        )
    )
    await upsert_external_courses(
        session,
        user_id=user_id,
        platform_id=platform_id,
        courses=courses,
        commit=False,
    )
    await session.commit()


async def list_cached_courses(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    platform_id: str | None = None,
) -> list[ExternalCourseCache]:
    query = select(ExternalCourseCache).where(ExternalCourseCache.user_id == user_id)
    if platform_id is not None:
        query = query.where(ExternalCourseCache.platform_id == platform_id)
    result = await session.execute(query.order_by(ExternalCourseCache.title))
    return list(result.scalars())
