from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.domain.cache.parse import parse_catalog_course
from app.infra.models import ExternalCourseCache
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


async def upsert_external_courses(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    platform_id: str,
    courses: list[dict[str, object]],
    commit: bool = True,
) -> None:
    now = datetime.now(UTC)
    for course in courses:
        parsed = parse_catalog_course(course)
        if parsed is None:
            continue
        metadata = {
            "description": parsed["description"],
            "author": parsed["author"],
            "language": parsed["language"],
            "tags": parsed["tags"],
            "enrolled": parsed["enrolled"],
            "is_paid": parsed["is_paid"],
        }
        stmt = insert(ExternalCourseCache).values(
            platform_id=platform_id,
            external_id=parsed["external_id"],
            user_id=user_id,
            title=parsed["title"],
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
                "title": parsed["title"],
                "metadata_json": metadata,
                "indexed_at": now,
            },
        )
        await session.execute(stmt)
    if commit:
        await session.commit()
