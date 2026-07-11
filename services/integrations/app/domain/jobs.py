from __future__ import annotations

import uuid
from pathlib import Path

import httpx
from app.config import IntegrationsSettings
from app.domain.pack_builder import (
    normalized_from_adapter,
    summarize_report,
    write_pack_to_disk,
)
from app.infra.models import ImportJob
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.catalog_schemas import PackUploadResponse
from studio_contracts.integration_schemas import ImportJobStatus, ImportReport
from studio_integration_sdk.registry import AdapterModule

_ACTIVE_STATUSES = frozenset({"pending", "fetching", "normalizing", "building"})


class JobError(Exception):
    __slots__ = ("detail",)

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


async def create_import_job(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    platform_id: str,
    course_id: str,
) -> ImportJob:
    existing = await session.execute(
        select(ImportJob).where(
            ImportJob.user_id == user_id,
            ImportJob.platform_id == platform_id,
            ImportJob.external_course_id == course_id,
            ImportJob.status.in_(_ACTIVE_STATUSES),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise JobError("import already in progress")

    job = ImportJob(
        user_id=user_id,
        platform_id=platform_id,
        external_course_id=course_id,
        status="pending",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


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


async def run_import_job(
    session: AsyncSession,
    client: httpx.AsyncClient,
    settings: IntegrationsSettings,
    adapter: AdapterModule,
    job: ImportJob,
) -> ImportJob:
    try:
        return await _execute_import(session, client, settings, adapter, job)
    except Exception as exc:
        await _mark_failed(session, job, exc)
        raise


async def _execute_import(
    session: AsyncSession,
    client: httpx.AsyncClient,
    settings: IntegrationsSettings,
    adapter: AdapterModule,
    job: ImportJob,
) -> ImportJob:
    await _set_status(session, job, "fetching")
    pack_raw, report_raw = adapter.import_course(course_id=job.external_course_id)

    await _set_status(session, job, "normalizing")
    normalized = normalized_from_adapter(pack_raw)
    report = summarize_report(ImportReport.model_validate(report_raw))
    report_json = report.model_dump(mode="json")

    await _set_status(session, job, "building")
    built = write_pack_to_disk(
        normalized,
        packs_root=settings.packs_root,
        user_id=job.user_id,
    )
    registered = await _register_with_catalog(
        client,
        settings,
        user_id=job.user_id,
        manifest=built.manifest,
        disk_path=built.disk_path,
        external_id=normalized.external_id,
        source=normalized.platform,
        import_report=report_json,
    )

    job.status = "done"
    job.pack_version_id = registered.version_id
    job.report = report_json
    job.error = None
    await session.commit()
    await session.refresh(job)
    return job


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


async def _register_with_catalog(
    client: httpx.AsyncClient,
    settings: IntegrationsSettings,
    *,
    user_id: uuid.UUID,
    manifest: dict[str, object],
    disk_path: Path,
    external_id: str,
    source: str,
    import_report: dict[str, object],
) -> PackUploadResponse:
    response = await client.post(
        f"{settings.catalog_service_url}/internal/v1/catalog/packs/register",
        headers={"X-User-Id": str(user_id)},
        json={
            "manifest": manifest,
            "disk_path": disk_path.as_posix(),
            "external_id": external_id,
            "source": source,
            "import_report": import_report,
        },
    )
    if response.is_error:
        detail = response.text
        raise JobError(detail or "catalog registration failed")
    return PackUploadResponse.model_validate(response.json())
