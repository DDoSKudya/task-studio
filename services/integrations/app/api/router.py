from __future__ import annotations

import uuid

from app.api.deps import Adapters, DbSession, Settings
from app.domain.cache import list_cached_courses, upsert_external_courses
from app.domain.jobs import JobError, create_import_job, get_import_job
from app.domain.messaging import publish_external_courses_for_index, publish_import_job
from app.infra.models import ExternalCourseCache, ImportJob
from fastapi import APIRouter, HTTPException, status
from studio_common.internal import InternalUserId
from studio_contracts.integration_schemas import (
    AdapterInfo,
    ExternalCourseSummary,
    ImportJobResponse,
    ImportReport,
    StartImportRequest,
    parse_job_status,
)
from studio_integration_sdk.registry import AdapterModule

router = APIRouter(prefix="/internal/v1/integrations", tags=["integrations"])


def _require_adapter(adapters: dict[str, AdapterModule], platform_id: str) -> AdapterModule:
    adapter = adapters.get(platform_id)
    if adapter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="platform not found")
    return adapter


def _to_course_summary(row: ExternalCourseCache) -> ExternalCourseSummary:
    return ExternalCourseSummary(
        platform=row.platform_id,
        external_id=row.external_id,
        title=row.title,
        description=str(row.metadata_json.get("description", "")),
    )


def _job_response(job: ImportJob) -> ImportJobResponse:
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


@router.get("", response_model=list[AdapterInfo])
async def list_adapters(adapters: Adapters) -> list[AdapterInfo]:
    return [adapter.info for adapter in adapters.values()]


@router.get("/{platform_id}/catalog", response_model=list[ExternalCourseSummary])
async def platform_catalog(
    platform_id: str,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
    adapters: Adapters,
) -> list[ExternalCourseSummary]:
    adapter = _require_adapter(adapters, platform_id)
    remote = adapter.list_catalog(user_id=str(user_id))
    await upsert_external_courses(
        session,
        user_id=user_id,
        platform_id=platform_id,
        courses=remote,
    )
    await publish_external_courses_for_index(
        settings,
        user_id=user_id,
        platform_id=platform_id,
        courses=remote,
    )
    cached = await list_cached_courses(session, user_id=user_id, platform_id=platform_id)
    return [_to_course_summary(row) for row in cached]


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
    _require_adapter(adapters, platform_id)

    try:
        job = await create_import_job(
            session,
            user_id=user_id,
            platform_id=platform_id,
            course_id=body.course_id,
        )
    except JobError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    await publish_import_job(
        settings,
        job_id=job.id,
        user_id=user_id,
        platform_id=platform_id,
    )
    return _job_response(job)


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
    return _job_response(job)
