from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.infra.models import ExternalCourseCache
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


def parse_catalog_course(course: dict[str, object]) -> tuple[str, str, str] | None:
    external_id = course.get("id")
    title = course.get("title")
    if not isinstance(external_id, str) or not isinstance(title, str):
        return None
    description = course.get("description")
    return external_id, title, description if isinstance(description, str) else ""


async def upsert_external_courses(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    platform_id: str,
    courses: list[dict[str, object]],
) -> None:
    now = datetime.now(UTC)
    for course in courses:
        parsed = parse_catalog_course(course)
        if parsed is None:
            continue
        external_id, title, description = parsed
        metadata = {"description": description}
        stmt = insert(ExternalCourseCache).values(
            platform_id=platform_id,
            external_id=external_id,
            user_id=user_id,
            title=title,
            metadata_json=metadata,
            indexed_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                ExternalCourseCache.platform_id,
                ExternalCourseCache.external_id,
                ExternalCourseCache.user_id,
            ],
            set_={
                "title": title,
                "metadata_json": metadata,
                "indexed_at": now,
            },
        )
        await session.execute(stmt)
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
