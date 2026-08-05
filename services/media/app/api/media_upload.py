from __future__ import annotations

import asyncio
import uuid
from typing import Annotated

from app.api.asset_ids import MAX_UPLOAD_BYTES, require_safe_asset_id, safe_filename
from app.api.deps import MinioClient, Settings
from app.storage import put_object_bytes, user_object_key
from fastapi import File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from studio_common.internal import InternalUserId


class MediaUploadResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    asset_id: str
    object_key: str
    content_type: str
    size: int = Field(ge=0)


async def upload_media_asset(
    user_id: InternalUserId,
    settings: Settings,
    client: MinioClient,
    file: Annotated[UploadFile, File()],
    asset_id: Annotated[str | None, Form()] = None,
) -> MediaUploadResponse:
    raw_id = (
        asset_id or ""
    ).strip() or f"uploads/{uuid.uuid4().hex}_{safe_filename(file.filename)}"
    require_safe_asset_id(raw_id)
    payload = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="file too large"
        )
    if not payload:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="empty file")

    content_type = file.content_type or "application/octet-stream"
    object_key = user_object_key(user_id, raw_id)
    await asyncio.to_thread(
        put_object_bytes,
        client,
        settings,
        object_key,
        payload,
        content_type=content_type,
    )
    return MediaUploadResponse(
        asset_id=raw_id,
        object_key=object_key,
        content_type=content_type,
        size=len(payload),
    )
