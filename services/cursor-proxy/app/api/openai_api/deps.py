from __future__ import annotations

import httpx
from fastapi import HTTPException, Request

from app.config import CursorProxyConfig


def require_bearer_api_key(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization Bearer token required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Authorization Bearer token required")
    return token.strip()


def proxy_config(request: Request) -> CursorProxyConfig:
    return request.app.state.config


def proxy_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http
