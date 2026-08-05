from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

import httpx
from app.upstream import call_service, parse_upstream, raise_for_upstream_error
from fastapi import HTTPException
from studio_contracts.catalog_schemas import PackDetail

if TYPE_CHECKING:
    from app.config import StudioApiSettings

log = logging.getLogger("studio-api.catalog_delete")


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
    version_id_strings = [str(item) for item in version_ids]

    # Удаление пакета для пользователя критично; сайд-эффекты (abandon/unindex) не должны
    # ломать основной запрос, даже если соседние сервисы временно недоступны.
    try:
        abandon_upstream = await call_service(
            client,
            settings.sessions_service_url,
            "post",
            "/internal/v1/sessions/abandon-by-pack-versions",
            user_id=user_id,
            json={"pack_version_ids": version_id_strings},
        )
        raise_for_upstream_error(abandon_upstream)
    except HTTPException as exc:
        log.warning(
            "pack_delete_abandon_failed pack_id=%s error=%s error_type=%s",
            str(pack_id),
            str(exc),
            type(exc).__name__,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "pack_delete_abandon_failed_unexpected pack_id=%s error=%s error_type=%s",
            str(pack_id),
            str(exc),
            type(exc).__name__,
        )

    try:
        unindex_upstream = await call_service(
            client,
            settings.search_service_url,
            "post",
            "/internal/v1/search/unindex-pack",
            user_id=user_id,
            json={
                "pack_id": str(pack_id),
                "pack_version_ids": version_id_strings,
            },
        )
        raise_for_upstream_error(unindex_upstream)
    except HTTPException as exc:
        log.warning(
            "pack_delete_unindex_failed pack_id=%s error=%s error_type=%s",
            str(pack_id),
            str(exc),
            type(exc).__name__,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "pack_delete_unindex_failed_unexpected pack_id=%s error=%s error_type=%s",
            str(pack_id),
            str(exc),
            type(exc).__name__,
        )

    delete_upstream = await call_service(
        client,
        settings.catalog_service_url,
        "delete",
        f"/internal/v1/catalog/packs/{pack_id}",
        user_id=user_id,
    )
    raise_for_upstream_error(delete_upstream)
