from __future__ import annotations

from collections.abc import Awaitable, Callable

import jwt
from app.config import StudioApiSettings
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response
from studio_common.security.jwt_tokens import decode_user_id

PUBLIC_AUTH_PATHS = frozenset(
    {
        "/v1/auth/register",
        "/v1/auth/login",
        "/v1/auth/logout",
    }
)


def register_auth_middleware(
    app: FastAPI,
    *,
    public_paths: frozenset[str] = PUBLIC_AUTH_PATHS,
) -> None:
    async def enforce_auth(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings: StudioApiSettings = request.app.state.settings
        request.state.user_id = None
        path = request.url.path

        if path in public_paths or not path.startswith("/v1/"):
            return await call_next(request)

        token = request.cookies.get(settings.cookie_name)
        if not token:
            return JSONResponse(status_code=401, content={"detail": "authentication required"})

        try:
            request.state.user_id = decode_user_id(token, secret=settings.jwt_secret)
        except (jwt.PyJWTError, ValueError):
            return JSONResponse(status_code=401, content={"detail": "invalid token"})

        return await call_next(request)

    app.middleware("http")(enforce_auth)
