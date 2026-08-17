from __future__ import annotations

from typing import Annotated

from app.api.auth_routes.support import (
    call_auth,
    clear_auth_cookie,
    prepare_settings_patch,
    rotate_access_cookie,
    sign_in,
)
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import parse_upstream
from fastapi import APIRouter, Depends, Response, status
from studio_common.security.auth_schemas import (
    AuthSuccess,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    SettingsPatch,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.post("/register", response_model=AuthSuccess, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    settings: Settings,
    client: UpstreamClient,
) -> AuthSuccess:
    return await sign_in("register", body, response, settings, client)


@router.post("/login", response_model=AuthSuccess)
async def login(
    body: LoginRequest,
    response: Response,
    settings: Settings,
    client: UpstreamClient,
) -> AuthSuccess:
    return await sign_in("login", body, response, settings, client)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: Settings) -> Response:
    clear_auth_cookie(response, settings)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/refresh", response_model=MeResponse)
async def refresh(
    response: Response,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> MeResponse:
    upstream = await call_auth(
        client,
        settings,
        "get",
        "/internal/v1/auth/me",
        user_id=str(user_id),
    )
    body = parse_upstream(upstream, MeResponse)
    rotate_access_cookie(response, user_id, settings)
    return body


@router.get("/me", response_model=MeResponse)
async def me(
    response: Response,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> MeResponse:
    upstream = await call_auth(
        client,
        settings,
        "get",
        "/internal/v1/auth/me",
        user_id=str(user_id),
    )
    body = parse_upstream(upstream, MeResponse)
    rotate_access_cookie(response, user_id, settings)
    return body


@router.patch("/me/settings", response_model=MeResponse)
async def patch_settings(
    body: SettingsPatch,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> MeResponse:
    prepared = await prepare_settings_patch(
        body,
        settings,
        client=client,
        user_id=str(user_id),
    )
    upstream = await call_auth(
        client,
        settings,
        "patch",
        "/internal/v1/auth/me/settings",
        user_id=str(user_id),
        json=prepared,
    )
    return parse_upstream(upstream, MeResponse)
