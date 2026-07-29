from __future__ import annotations

import httpx
from app.config import IntegrationsSettings
from app.domain.credentials import fetch_platform_credentials
from app.infra.models import ImportJob
from sqlalchemy.ext.asyncio import AsyncSession
from studio_integration_sdk.registry import AdapterModule

from .catalog_register import register_with_catalog
from .execute_pipeline import build_and_register_import
from .lifecycle import _mark_failed, _set_status
from .paths import resolve_upload_archive

_register_with_catalog = register_with_catalog


async def run_import_job(
    session: AsyncSession,
    client: httpx.AsyncClient,
    settings: IntegrationsSettings,
    adapter: AdapterModule,
    job: ImportJob,
) -> ImportJob:
    if job.status in {"done", "failed"}:
        return job
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
                                                                     
    if job.status == "pending":
        await _set_status(session, job, "fetching")
    credentials = await fetch_platform_credentials(
        client,
        auth_service_url=settings.auth_service_url,
        user_id=job.user_id,
        platform_id=job.platform_id,
    )
    import_kwargs: dict[str, object] = dict(credentials)
    archive_path = resolve_upload_archive(
        packs_root=settings.packs_root,
        user_id=job.user_id,
        course_id=job.external_course_id,
    )
    if archive_path is not None:
        import_kwargs["archive_path"] = str(archive_path)
    return await build_and_register_import(
        session,
        client,
        settings,
        adapter,
        job,
        import_kwargs=import_kwargs,
    )
