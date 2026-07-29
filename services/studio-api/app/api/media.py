                                                

from __future__ import annotations

from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

router = APIRouter(prefix="/v1/media", tags=["media"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.post("/upload")
async def upload_media_asset(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
    file: Annotated[UploadFile, File()],
    asset_id: Annotated[str | None, Form()] = None,
) -> Response:
    files = {
        "file": (
            file.filename or "upload.bin",
            await file.read(),
            file.content_type or "application/octet-stream",
        )
    }
    data = {"asset_id": asset_id} if asset_id else None
    upstream = await client.post(
        f"{settings.media_service_url}/internal/v1/media/upload",
        headers={"X-User-Id": str(user_id)},
        files=files,
        data=data,
    )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


@router.get("/{asset_id:path}", response_model=None)
async def get_media_asset(
    asset_id: str,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> Response:
                                                                        
    upstream = await client.get(
        f"{settings.media_service_url}/internal/v1/media/{asset_id}",
        headers={"X-User-Id": str(user_id)},
    )
    if upstream.is_error:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    media_type = upstream.headers.get("content-type") or "application/octet-stream"
    headers: dict[str, str] = {}
    if length := upstream.headers.get("content-length"):
        headers["content-length"] = length
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=media_type,
        headers=headers,
    )
