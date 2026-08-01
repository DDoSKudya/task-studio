from __future__ import annotations

import uuid

from app.infra.models import ImportJob
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.integration_schemas import ImportJobStatus

from .create import create_import_job, fail_stale_import_jobs, supersede_active_import_jobs
from .errors import JobError

__all__ = [
    "supersede_active_import_jobs",
    "fail_stale_import_jobs",
    "create_import_job",
    "get_import_job",
    "claim_import_job",
    "_mark_failed",
    "_set_status",
]


async def get_import_job(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
) -> ImportJob:
    job = await session.get(ImportJob, job_id)
    if job is None or job.user_id != user_id:
        raise JobError("import job not found")
    return job


async def claim_import_job(session: AsyncSession, job: ImportJob) -> bool:
    result = await session.execute(
        update(ImportJob)
        .where(ImportJob.id == job.id, ImportJob.status == "pending")
        .values(status="fetching")
        .returning(ImportJob.id)
    )
    claimed = result.scalar_one_or_none() is not None
    await session.commit()
    if claimed:
        await session.refresh(job)
    return claimed


async def _mark_failed(session: AsyncSession, job: ImportJob, exc: Exception) -> None:
    job.status = "failed"
    job.error = str(exc)
    await session.commit()
    await session.refresh(job)


async def _set_status(
    session: AsyncSession,
    job: ImportJob,
    status: ImportJobStatus,
) -> None:
    job.status = status
    await session.commit()
    await session.refresh(job)
