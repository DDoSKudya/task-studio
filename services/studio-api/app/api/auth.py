from __future__ import annotations

from typing import Annotated, Literal, assert_never

import httpx
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import parse_upstream
from fastapi import APIRouter, Depends, Response, status
from studio_common.auth_schemas import (
    AuthSuccess,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    SettingsPatch,
)
from studio_common.jwt_tokens import create_access_token

router = APIRouter(prefix="/v1/auth", tags=["auth"])

type AuthAction = Literal["register", "login"]
type AuthHttpMethod = Literal["get", "post", "patch"]

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


async def _call_auth(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    method: AuthHttpMethod,
    path: str,
    *,
    user_id: str | None = None,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    url = f"{settings.auth_service_url}{path}"
    headers = {"X-User-Id": user_id} if user_id is not None else None
    match method:
        case "get":
            return await client.get(url, headers=headers)
        case "post":
            return await client.post(url, headers=headers, json=json)
        case "patch":
            return await client.patch(url, headers=headers, json=json)
        case unreachable:
            assert_never(unreachable)


def _set_auth_cookie(response: Response, token: str, settings: StudioApiSettings) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_hours * 3600,
        path="/",
    )


def _clear_auth_cookie(response: Response, settings: StudioApiSettings) -> None:
    response.delete_cookie(key=settings.cookie_name, path="/")


def _issue_session(
    response: Response,
    body: AuthSuccess,
    settings: StudioApiSettings,
) -> AuthSuccess:
    token = create_access_token(
        body.user.id,
        secret=settings.jwt_secret,
        expire_hours=settings.jwt_expire_hours,
    )
    _set_auth_cookie(response, token, settings)
    return body


async def _sign_in(
    action: AuthAction,
    body: RegisterRequest | LoginRequest,
    response: Response,
    settings: StudioApiSettings,
    client: httpx.AsyncClient,
) -> AuthSuccess:
    upstream = await _call_auth(
        client,
        settings,
        "post",
        f"/internal/v1/auth/{action}",
        json=body.model_dump(mode="json"),
    )
    auth = parse_upstream(upstream, AuthSuccess)
    return _issue_session(response, auth, settings)


@router.post("/register", response_model=AuthSuccess, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    settings: Settings,
    client: UpstreamClient,
) -> AuthSuccess:
    return await _sign_in("register", body, response, settings, client)


@router.post("/login", response_model=AuthSuccess)
async def login(
    body: LoginRequest,
    response: Response,
    settings: Settings,
    client: UpstreamClient,
) -> AuthSuccess:
    return await _sign_in("login", body, response, settings, client)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: Settings) -> Response:
    _clear_auth_cookie(response, settings)
    return response


@router.get("/me", response_model=MeResponse)
async def me(user_id: UserId, settings: Settings, client: UpstreamClient) -> MeResponse:
    upstream = await _call_auth(
        client,
        settings,
        "get",
        "/internal/v1/auth/me",
        user_id=str(user_id),
    )
    return parse_upstream(upstream, MeResponse)


@router.patch("/me/settings", response_model=MeResponse)
async def patch_settings(
    body: SettingsPatch,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> MeResponse:
    upstream = await _call_auth(
        client,
        settings,
        "patch",
        "/internal/v1/auth/me/settings",
        user_id=str(user_id),
        json=body.model_dump(mode="json", exclude_unset=True),
    )
    return parse_upstream(upstream, MeResponse)
