from __future__ import annotations

import uuid

import httpx
from app.config import SearchSettings
from studio_contracts.api.catalog_schemas import PackVersionContext


async def fetch_pack_context(
    http: httpx.AsyncClient,
    settings: SearchSettings,
    user_id: uuid.UUID,
    pack_version_id: uuid.UUID,
) -> PackVersionContext:
    response = await http.get(
        f"{settings.catalog_service_url}/internal/v1/catalog/pack-versions/{pack_version_id}",
        headers={"X-User-Id": str(user_id)},
    )
    response.raise_for_status()
    return PackVersionContext.model_validate(response.json())
