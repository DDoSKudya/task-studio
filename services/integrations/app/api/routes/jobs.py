from __future__ import annotations

import uuid

from app.api.deps import Adapters, DbSession, Settings
from app.api.routes.helpers import job_response, require_adapter
from app.api.routes.jobs_upload import router as upload_router
from app.domain.jobs import JobError, create_import_job, get_import_job, import_job_needs_republish
from app.domain.messaging import publish_import_job
from fastapi import APIRouter, HTTPException, status
from studio_common.internal import InternalUserId
from studio_contracts.integration_schemas import ImportJobResponse, StartImportRequest

router = APIRouter()
router.include_router(upload_router)


@router.post(
    "/{platform_id}/import",
    response_model=ImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_import(
    platform_id: str,
    body: StartImportRequest,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
    adapters: Adapters,
) -> ImportJobResponse:
    require_adapter(adapters, platform_id)

    try:
        job, created = await create_import_job(
            session,
            user_id=user_id,
            platform_id=platform_id,
            course_id=body.course_id,
            force=body.force,
        )
    except JobError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    if created or import_job_needs_republish(job):
        await publish_import_job(
            settings,
            job_id=job.id,
            user_id=user_id,
            platform_id=platform_id,
        )
    return job_response(job)


@router.get("/jobs/{job_id}", response_model=ImportJobResponse)
async def get_job(
    job_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
) -> ImportJobResponse:
    try:
        job = await get_import_job(session, user_id=user_id, job_id=job_id)
    except JobError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail) from exc
    return job_response(job)
