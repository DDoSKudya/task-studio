from __future__ import annotations

import uuid
from typing import Annotated

from app.api.catalog_routes.delete import delete_pack_with_cleanup
from app.api.catalog_routes.mutate import router as mutate_router
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream, parse_upstream_list
from fastapi import APIRouter, Depends, status
from studio_contracts.catalog_schemas import PackDetail, PackSummary

router = APIRouter(prefix="/v1/catalog", tags=["catalog"])
router.include_router(mutate_router)

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.get("/packs", response_model=list[PackSummary])
async def list_packs(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> list[PackSummary]:
    upstream = await call_service(
        client,
        settings.catalog_service_url,
        "get",
        "/internal/v1/catalog/packs",
        user_id=user_id,
    )
    return parse_upstream_list(upstream, PackSummary)


@router.get("/packs/{pack_id}", response_model=PackDetail)
async def get_pack(
    pack_id: uuid.UUID,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> PackDetail:
    upstream = await call_service(
        client,
        settings.catalog_service_url,
        "get",
        f"/internal/v1/catalog/packs/{pack_id}",
        user_id=user_id,
    )
    return parse_upstream(upstream, PackDetail)


@router.delete("/packs/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pack(
    pack_id: uuid.UUID,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> None:
    await delete_pack_with_cleanup(client, settings, user_id=user_id, pack_id=pack_id)
