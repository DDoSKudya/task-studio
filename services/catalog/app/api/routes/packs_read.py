from __future__ import annotations

import uuid

from app.api.deps import DbSession
from app.domain.packs import (
    activate_pack_version,
    get_user_pack,
    get_user_pack_version,
    list_user_packs,
)
from fastapi import APIRouter
from studio_common.security.internal import InternalUserId
from studio_contracts.api.catalog_schemas import (
    ActivatePackRequest,
    PackDetail,
    PackSummary,
    PackVersionContext,
    PackVersionInfo,
)

from ..mappers import pack_detail, pack_summary, pack_version_info

router = APIRouter()


@router.get("/packs", response_model=list[PackSummary])
async def list_packs(user_id: InternalUserId, session: DbSession) -> list[PackSummary]:
    rows = await list_user_packs(session, user_id)
    return [pack_summary(pack, version, installed_at) for pack, version, installed_at in rows]


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
        object_key=pack_version.object_key,
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
