from __future__ import annotations

import uuid

from app.infra.models import ImportJob
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .cleanup import _ACTIVE_STATUSES, fail_stale_import_jobs, supersede_active_import_jobs
from .staleness import import_job_is_stale

__all__ = [
    "create_import_job",
    "fail_stale_import_jobs",
    "supersede_active_import_jobs",
]


async def create_import_job(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    platform_id: str,
    course_id: str,
    force: bool = False,
) -> tuple[ImportJob, bool]:
    if force:
        await supersede_active_import_jobs(
            session,
            user_id=user_id,
            platform_id=platform_id,
            course_id=course_id,
            reason="replaced by re-download",
        )
    else:
        existing = await session.execute(
            select(ImportJob)
            .where(
                ImportJob.user_id == user_id,
                ImportJob.platform_id == platform_id,
                ImportJob.external_course_id == course_id,
                ImportJob.status.in_(_ACTIVE_STATUSES),
            )
            .order_by(ImportJob.created_at.desc())
            .limit(1)
        )
        active = existing.scalar_one_or_none()
        if active is not None:
            if not import_job_is_stale(active):
                return active, False
            active.status = "failed"
            active.error = "import timed out"
            await session.commit()

    job = ImportJob(
        user_id=user_id,
        platform_id=platform_id,
        external_course_id=course_id,
        status="pending",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job, True
