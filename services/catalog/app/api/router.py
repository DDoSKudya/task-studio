from __future__ import annotations

import uuid
from pathlib import Path

from app.api.deps import DbSession, Settings
from app.api.mappers import pack_detail, pack_summary, pack_upload_response, pack_version_info
from app.domain.packs import (
    activate_pack_version,
    delete_user_pack,
    get_user_pack,
    get_user_pack_version,
    list_user_packs,
    register_imported_pack,
    upload_pack,
)
from fastapi import APIRouter, UploadFile, status
from studio_common.internal import InternalUserId
from studio_contracts.catalog_schemas import (
    ActivatePackRequest,
    PackDetail,
    PackSummary,
    PackUploadResponse,
    PackVersionContext,
    PackVersionInfo,
    RegisterImportedPackRequest,
)

router = APIRouter(prefix="/internal/v1/catalog", tags=["catalog"])


@router.post(
    "/packs/register",
    response_model=PackUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_pack(
    body: RegisterImportedPackRequest,
    user_id: InternalUserId,
    session: DbSession,
) -> PackUploadResponse:
    uploaded = await register_imported_pack(
        session,
        user_id,
        manifest=body.manifest,
        disk_path=Path(body.disk_path),
        external_id=body.external_id,
        source=body.source,
        import_report=body.import_report,
    )
    return pack_upload_response(uploaded)


@router.get("/packs", response_model=list[PackSummary])
async def list_packs(user_id: InternalUserId, session: DbSession) -> list[PackSummary]:
    rows = await list_user_packs(session, user_id)
    return [pack_summary(pack, version, installed_at) for pack, version, installed_at in rows]


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
    )
    return pack_upload_response(uploaded)


@router.get("/pack-versions/{version_id}", response_model=PackVersionContext)
async def get_pack_version(
    version_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
) -> PackVersionContext:
    pack, pack_version = await get_user_pack_version(session, user_id, version_id)
    return PackVersionContext(
        id=pack_version.id,
        pack_id=pack.id,
        pack_title=pack.title,
        version=pack_version.version,
        manifest=pack_version.manifest,
        disk_path=pack_version.disk_path,
    )


@router.get("/packs/{pack_id}", response_model=PackDetail)
async def get_pack(
    pack_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
) -> PackDetail:
    pack, versions, active = await get_user_pack(session, user_id, pack_id)
    return pack_detail(pack, versions, active)


@router.post("/packs/{pack_id}/activate", response_model=PackVersionInfo)
async def activate_pack(
    pack_id: uuid.UUID,
    body: ActivatePackRequest,
    user_id: InternalUserId,
    session: DbSession,
) -> PackVersionInfo:
    pack_version = await activate_pack_version(session, user_id, pack_id, body.version)
    return pack_version_info(pack_version, active=True)


@router.delete("/packs/{pack_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pack(
    pack_id: uuid.UUID,
    user_id: InternalUserId,
    session: DbSession,
    settings: Settings,
) -> None:
    await delete_user_pack(
        session,
        user_id,
        pack_id,
        packs_root=settings.packs_root,
    )
