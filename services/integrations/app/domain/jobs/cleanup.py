from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.infra.models import ImportJob
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .staleness import import_job_is_stale

_ACTIVE_STATUSES = frozenset({"pending", "fetching", "normalizing", "building"})


async def supersede_active_import_jobs(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    platform_id: str,
    course_id: str,
    reason: str = "replaced by newer import",
) -> int:
    result = await session.execute(
        update(ImportJob)
        .where(
            ImportJob.user_id == user_id,
            ImportJob.platform_id == platform_id,
            ImportJob.external_course_id == course_id,
            ImportJob.status.in_(_ACTIVE_STATUSES),
        )
        .values(status="failed", error=reason)
        .returning(ImportJob.id)
    )
    ids = list(result.scalars().all())
    if ids:
        await session.commit()
    return len(ids)


async def fail_stale_import_jobs(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> int:
    clock = now or datetime.now(UTC)
    result = await session.execute(select(ImportJob).where(ImportJob.status.in_(_ACTIVE_STATUSES)))
    stale = [job for job in result.scalars().all() if import_job_is_stale(job, now=clock)]
    if not stale:
        return 0
    for job in stale:
        job.status = "failed"
        job.error = "import timed out"
    await session.commit()
    return len(stale)
