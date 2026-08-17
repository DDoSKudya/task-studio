from __future__ import annotations

import uuid

from app.api.deps import Adapters, DbSession, Settings
from app.api.routes.common.helpers import (
    _UPLOAD_PLATFORMS,
    archive_suffix,
    job_response,
    require_adapter,
)
from app.domain.jobs import JobError, create_import_job, import_job_needs_republish, staging_dir
from app.domain.messaging import publish_import_job
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from studio_common.security.internal import InternalUserId
from studio_contracts.api.integration_schemas import ImportJobResponse

router = APIRouter()


@router.post(
    "/{platform_id}/upload",
    response_model=ImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_archive(
    platform_id: str,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
    adapters: Adapters,
    file: UploadFile = File(...),
) -> ImportJobResponse:
    adapter = require_adapter(adapters, platform_id)
    if platform_id not in _UPLOAD_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="platform does not support archive upload",
        )
    if not adapter.info.capabilities.import_course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="import not supported")

    filename = file.filename or "course.zip"
    suffix = archive_suffix(filename)
    if suffix is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expected .zip, .tar.gz, or .mbz archive",
        )

    file_id = uuid.uuid4()
    dest = staging_dir(settings.packs_root, user_id) / f"{file_id}{suffix}"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty archive")
    dest.write_bytes(content)

    try:
        job, created = await create_import_job(
            session,
            user_id=user_id,
            platform_id=platform_id,
            course_id=f"upload:{file_id}",
        )
    except JobError as exc:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    if created or import_job_needs_republish(job):
        await publish_import_job(
            settings,
            job_id=job.id,
            user_id=user_id,
            platform_id=platform_id,
        )
    return job_response(job)
