from __future__ import annotations

from typing import Annotated

from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/v1/media", tags=["media"])

_REDIRECT_STATUS_CODES = frozenset({301, 302, 307, 308})

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.get("/{asset_id:path}")
async def get_media_asset(
    asset_id: str,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> RedirectResponse:
    upstream = await client.get(
        f"{settings.media_service_url}/internal/v1/media/{asset_id}",
        headers={"X-User-Id": str(user_id)},
        follow_redirects=False,
    )
    if upstream.status_code in _REDIRECT_STATUS_CODES:
        location = upstream.headers.get("location")
        if not location:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="missing redirect location",
            )
        return RedirectResponse(url=location, status_code=upstream.status_code)
    if upstream.is_error:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="unexpected media response")
