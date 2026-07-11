from __future__ import annotations

import uuid
from typing import Annotated, cast

import httpx
from fastapi import Depends, HTTPException, Request, status


def require_user_id(request: Request) -> uuid.UUID:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )
    return user_id


def get_upstream_client(request: Request) -> httpx.AsyncClient:
    client = getattr(request.app.state, "upstream_client", None)
    if client is None:
        msg = "upstream client is not initialized"
        raise RuntimeError(msg)
    return cast(httpx.AsyncClient, client)


type UserId = Annotated[uuid.UUID, Depends(require_user_id)]
type UpstreamClient = Annotated[httpx.AsyncClient, Depends(get_upstream_client)]
