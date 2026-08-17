from __future__ import annotations

import uuid

import httpx
from app.config import SessionsSettings
from app.domain.common.session_errors import SessionError
from studio_contracts.api.catalog_schemas import PackVersionContext


async def fetch_pack_version(
    client: httpx.AsyncClient,
    settings: SessionsSettings,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> PackVersionContext:
    try:
        response = await client.get(
            f"{settings.catalog_service_url}/internal/v1/catalog/pack-versions/{pack_version_id}",
            headers={"X-User-Id": str(user_id)},
        )
    except httpx.HTTPError as exc:
        raise SessionError(503, "catalog unavailable") from exc
    if response.status_code == 404:
        raise SessionError(404, "pack version not found")
    if response.is_error:
        raise SessionError(502, "catalog error")
    return PackVersionContext.model_validate(response.json())
