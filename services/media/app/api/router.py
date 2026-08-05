from __future__ import annotations

import asyncio

from app.api.asset_ids import require_safe_asset_id
from app.api.deps import MinioClient, Settings
from app.api.media_upload import MediaUploadResponse, upload_media_asset
from app.storage import (
    get_object_stream,
    object_exists,
    remove_object,
    user_object_key,
)
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from studio_common.internal import InternalUserId

router = APIRouter(prefix="/internal/v1/media", tags=["media"])

__all__ = ["router", "MediaUploadResponse", "upload_media_asset"]


@router.get("/{asset_id:path}", response_model=None)
async def get_media_asset(
    asset_id: str,
    user_id: InternalUserId,
    settings: Settings,
    client: MinioClient,
) -> StreamingResponse:
    require_safe_asset_id(asset_id)
    object_key = user_object_key(user_id, asset_id)
    exists = await asyncio.to_thread(object_exists, client, settings, object_key)
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset not found")
    stream, content_type, length = await asyncio.to_thread(
        get_object_stream,
        client,
        settings,
        object_key,
    )
    headers: dict[str, str] = {}
    if length is not None:
        headers["content-length"] = str(length)
    return StreamingResponse(
        stream,
        media_type=content_type or "application/octet-stream",
        headers=headers,
    )


@router.delete("/{asset_id:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media_asset(
    asset_id: str,
    user_id: InternalUserId,
    settings: Settings,
    client: MinioClient,
) -> Response:
    require_safe_asset_id(asset_id)
    object_key = user_object_key(user_id, asset_id)
    await asyncio.to_thread(remove_object, client, settings, object_key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router.add_api_route(
    "/upload",
    upload_media_asset,
    methods=["POST"],
    response_model=MediaUploadResponse,
)
