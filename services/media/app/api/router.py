from __future__ import annotations

from app.api.deps import MinioClient, Settings
from app.config import object_exists, presign_get_url, user_object_key
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from studio_common.internal import InternalUserId

router = APIRouter(prefix="/internal/v1/media", tags=["media"])


@router.get("/{asset_id:path}")
async def get_media_asset(
    asset_id: str,
    user_id: InternalUserId,
    settings: Settings,
    client: MinioClient,
) -> RedirectResponse:
    object_key = user_object_key(user_id, asset_id)
    if not object_exists(client, settings, object_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset not found")
    url = presign_get_url(client, settings, object_key)
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
