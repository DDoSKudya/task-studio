from __future__ import annotations

import uuid

from app.api.deps import DbSession, Settings
from app.api.routes.packs_read import router as packs_read_router
from app.domain.packs import delete_user_pack
from fastapi import APIRouter, status
from studio_common.internal import InternalUserId

router = APIRouter()
router.include_router(packs_read_router)


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
        media_service_url=settings.media_service_url,
    )
