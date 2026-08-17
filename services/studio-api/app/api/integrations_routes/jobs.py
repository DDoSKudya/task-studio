from __future__ import annotations

import uuid
from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream
from fastapi import APIRouter, Depends, File, UploadFile
from studio_contracts.api.integration_schemas import (
    EnrollCourseRequest,
    EnrollCourseResponse,
    ImportJobResponse,
    StartImportRequest,
)

router = APIRouter(tags=["integrations"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.post("/v1/integrations/{platform_id}/enroll", response_model=EnrollCourseResponse)
async def enroll_integration_course(
    platform_id: str,
    body: EnrollCourseRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> EnrollCourseResponse:
    upstream = await call_service(
        client,
        settings.integrations_service_url,
        "post",
        f"/internal/v1/integrations/{platform_id}/enroll",
        user_id=user_id,
        json=body.model_dump(mode="json"),
    )
    return parse_upstream(upstream, EnrollCourseResponse)


@router.post("/v1/integrations/{platform_id}/import", response_model=ImportJobResponse)
async def start_integration_import(
    platform_id: str,
    body: StartImportRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> ImportJobResponse:
    upstream = await call_service(
        client,
        settings.integrations_service_url,
        "post",
        f"/internal/v1/integrations/{platform_id}/import",
        user_id=user_id,
        json=body.model_dump(mode="json"),
    )
    return parse_upstream(upstream, ImportJobResponse)


@router.post("/v1/integrations/{platform_id}/upload", response_model=ImportJobResponse)
async def upload_integration_archive(
    platform_id: str,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
    file: UploadFile = File(...),
) -> ImportJobResponse:
    content = await file.read()
    filename = file.filename or "course.zip"
    content_type = file.content_type or "application/octet-stream"
    upstream = await call_service(
        client,
        settings.integrations_service_url,
        "post",
        f"/internal/v1/integrations/{platform_id}/upload",
        user_id=user_id,
        files={"file": (filename, content, content_type)},
    )
    return parse_upstream(upstream, ImportJobResponse)


@router.get("/v1/integrations/jobs/{job_id}", response_model=ImportJobResponse)
async def get_integration_job(
    job_id: uuid.UUID,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> ImportJobResponse:
    upstream = await call_service(
        client,
        settings.integrations_service_url,
        "get",
        f"/internal/v1/integrations/jobs/{job_id}",
        user_id=user_id,
    )
    return parse_upstream(upstream, ImportJobResponse)
