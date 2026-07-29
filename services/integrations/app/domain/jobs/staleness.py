from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.infra.models import ImportJob

_STALE_PENDING_AFTER = timedelta(minutes=15)
_STALE_IN_PROGRESS_AFTER = timedelta(minutes=6)
_REPUBLISH_PENDING_AFTER = timedelta(seconds=45)


def aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def import_job_is_stale(job: ImportJob, *, now: datetime | None = None) -> bool:
    clock = now or datetime.now(UTC)
    age = clock - aware(job.created_at)
    if job.status == "pending":
        return age > _STALE_PENDING_AFTER
    return age > _STALE_IN_PROGRESS_AFTER


def import_job_needs_republish(job: ImportJob, *, now: datetime | None = None) -> bool:
    if job.status != "pending":
        return False
    clock = now or datetime.now(UTC)
    return clock - aware(job.created_at) > _REPUBLISH_PENDING_AFTER
