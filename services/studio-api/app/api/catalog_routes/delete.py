from __future__ import annotations

import uuid

import httpx
from app.config import StudioApiSettings
from app.upstream import call_service, parse_upstream, raise_for_upstream_error
from studio_contracts.catalog_schemas import PackDetail


async def delete_pack_with_cleanup(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    *,
    user_id: uuid.UUID,
    pack_id: uuid.UUID,
) -> None:
    detail_upstream = await call_service(
        client,
        settings.catalog_service_url,
        "get",
        f"/internal/v1/catalog/packs/{pack_id}",
        user_id=user_id,
    )
    pack = parse_upstream(detail_upstream, PackDetail)
    version_ids = [version.id for version in pack.versions]

    upstream = await call_service(
        client,
        settings.catalog_service_url,
        "delete",
        f"/internal/v1/catalog/packs/{pack_id}",
        user_id=user_id,
    )
    raise_for_upstream_error(upstream)

    await call_service(
        client,
        settings.sessions_service_url,
        "post",
        "/internal/v1/sessions/abandon-by-pack-versions",
        user_id=user_id,
        json={
            "pack_version_ids": [str(item) for item in version_ids],
            "pack_titles": [pack.title],
        },
    )
    await call_service(
        client,
        settings.search_service_url,
        "post",
        "/internal/v1/search/unindex-pack",
        user_id=user_id,
        json={
            "pack_id": str(pack_id),
            "pack_version_ids": [str(item) for item in version_ids],
        },
    )
