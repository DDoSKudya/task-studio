from __future__ import annotations

from pathlib import Path

from app.infra.models import ImportJob
from studio_contracts.api.integration_schemas import (
    ImportJobResponse,
    ImportReport,
    parse_job_status,
)

_UPLOAD_PLATFORMS: frozenset[str] = frozenset()


def job_response(job: ImportJob) -> ImportJobResponse:
    report = ImportReport.model_validate(job.report) if isinstance(job.report, dict) else None
    return ImportJobResponse(
        id=job.id,
        platform_id=job.platform_id,
        external_course_id=job.external_course_id,
        status=parse_job_status(job.status),
        pack_version_id=job.pack_version_id,
        error=job.error,
        report=report,
        created_at=job.created_at,
    )


def archive_suffix(filename: str) -> str | None:
    lowered = filename.casefold()
    for suffix in (".tar.gz", ".tgz", ".mbz", ".zip", ".tar", ".gz"):
        if lowered.endswith(suffix):
            return suffix
    if "." not in Path(filename).name:
        return ".zip"
    return None
