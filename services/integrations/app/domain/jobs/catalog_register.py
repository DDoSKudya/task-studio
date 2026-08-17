from __future__ import annotations

import uuid
from pathlib import Path

import httpx
from app.config import IntegrationsSettings
from app.domain.jobs.errors import JobError
from studio_contracts.api.catalog_schemas import PackUploadResponse


async def register_with_catalog(
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
