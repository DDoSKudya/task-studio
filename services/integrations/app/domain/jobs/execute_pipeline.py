from __future__ import annotations

import httpx
from app.config import IntegrationsSettings
from app.domain.pack.builder import (
    normalized_from_adapter,
    summarize_report,
    write_pack_to_disk,
)
from app.infra.models import ImportJob
from sqlalchemy.ext.asyncio import AsyncSession
from studio_contracts.integration_schemas import ImportReport
from studio_integration_sdk.registry import AdapterModule

from .catalog_register import register_with_catalog
from .lifecycle import _set_status


async def build_and_register_import(
    session: AsyncSession,
    client: httpx.AsyncClient,
    settings: IntegrationsSettings,
    adapter: AdapterModule,
    job: ImportJob,
    *,
    import_kwargs: dict[str, object],
) -> ImportJob:
    pack_raw, report_raw = adapter.import_course(
        course_id=job.external_course_id,
        **import_kwargs,
    )

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
    registered = await register_with_catalog(
        client,
        settings,
        user_id=job.user_id,
        manifest=built.manifest,
        disk_path=built.disk_path,
        external_id=normalized.external_id,
        source=normalized.platform,
        import_report=report_json,
    )

    job.status = "partial" if report.truncated else "done"
    job.pack_version_id = registered.version_id
    job.report = report_json
    job.error = None
    await session.commit()
    await session.refresh(job)
    return job
