from __future__ import annotations

import uuid
from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import call_service, parse_upstream
from fastapi import APIRouter, Depends, File, UploadFile, status
from studio_contracts.catalog_schemas import (
    ActivatePackRequest,
    PackUploadResponse,
    PackVersionInfo,
)

router = APIRouter()

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]
type PackUpload = Annotated[UploadFile, File()]


@router.post(
    "/packs/upload",
    response_model=PackUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pack(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
    pack: PackUpload,
) -> PackUploadResponse:
    content = await pack.read()
    filename = pack.filename or "pack.studio-pack"
    content_type = pack.content_type or "application/zip"
    upstream = await call_service(
        client,
        settings.catalog_service_url,
        "post",
        "/internal/v1/catalog/packs/upload",
        user_id=user_id,
        files={"pack": (filename, content, content_type)},
    )
    return parse_upstream(upstream, PackUploadResponse)


@router.post("/packs/{pack_id}/activate", response_model=PackVersionInfo)
async def activate_pack(
    pack_id: uuid.UUID,
    body: ActivatePackRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> PackVersionInfo:
    upstream = await call_service(
        client,
        settings.catalog_service_url,
        "post",
        f"/internal/v1/catalog/packs/{pack_id}/activate",
        user_id=user_id,
        json=body.model_dump(mode="json"),
    )
    return parse_upstream(upstream, PackVersionInfo)
