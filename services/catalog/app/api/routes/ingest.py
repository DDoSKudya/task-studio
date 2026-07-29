from __future__ import annotations

from pathlib import Path

from app.api.deps import DbSession, Settings
from app.api.mappers import pack_upload_response
from app.domain.packs import register_imported_pack, upload_pack
from fastapi import APIRouter, UploadFile, status
from studio_common.internal import InternalUserId
from studio_contracts.catalog_schemas import (
    PackUploadResponse,
    RegisterImportedPackRequest,
)

router = APIRouter()


@router.post(
    "/packs/register",
    response_model=PackUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_pack(
    body: RegisterImportedPackRequest,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
) -> PackUploadResponse:
    uploaded = await register_imported_pack(
        session,
        user_id,
        manifest=body.manifest,
        disk_path=Path(body.disk_path),
        external_id=body.external_id,
        source=body.source,
        import_report=body.import_report,
        object_key=body.object_key,
        media_service_url=settings.media_service_url,
    )
    return pack_upload_response(uploaded)


@router.post(
    "/packs/upload",
    response_model=PackUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pack_endpoint(
    pack: UploadFile,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
) -> PackUploadResponse:
    archive = await pack.read()
    uploaded = await upload_pack(
        session,
        user_id,
        archive,
        packs_root=settings.packs_root,
        max_upload_bytes=settings.max_upload_bytes,
        media_service_url=settings.media_service_url,
    )
    return pack_upload_response(uploaded)
