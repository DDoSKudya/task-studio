from __future__ import annotations

import uuid
from typing import Annotated, Literal

import httpx
from app.config import StudioApiSettings, get_settings
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
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


def get_auth_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.auth_client


def require_user_id(request: Request) -> uuid.UUID:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication required",
        )
    return user_id


Settings = Annotated[StudioApiSettings, Depends(get_settings)]
AuthClient = Annotated[httpx.AsyncClient, Depends(get_auth_client)]
UserId = Annotated[uuid.UUID, Depends(require_user_id)]


def _upstream_detail(response: httpx.Response) -> str | list[dict[str, object]]:
    try:
        payload = response.json()
    except ValueError:
        return "upstream error"
    if not isinstance(payload, dict):
        return "upstream error"
    detail = payload.get("detail", "upstream error")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return detail
    return "upstream error"


def _parse_upstream[T: BaseModel](response: httpx.Response, model: type[T]) -> T:
    if response.is_error:
        raise HTTPException(
            status_code=response.status_code, detail=_upstream_detail(response)
        )
    return model.model_validate(response.json())


async def _call_auth(
    client: httpx.AsyncClient,
    settings: StudioApiSettings,
    method: str,
    path: str,
    *,
    user_id: uuid.UUID | None = None,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    url = f"{settings.auth_service_url}{path}"
    headers = {"X-User-Id": str(user_id)} if user_id is not None else None
    match method:
        case "get":
            return await client.get(url, headers=headers)
        case "post":
            return await client.post(url, headers=headers, json=json)
        case "patch":
            return await client.patch(url, headers=headers, json=json)
        case _:
            msg = f"unsupported auth upstream method: {method}"
            raise ValueError(msg)


def _set_auth_cookie(
    response: Response, token: str, settings: StudioApiSettings
) -> None:
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
    auth = _parse_upstream(upstream, AuthSuccess)
    return _issue_session(response, auth, settings)


@router.post(
    "/register", response_model=AuthSuccess, status_code=status.HTTP_201_CREATED
)
async def register(
    body: RegisterRequest,
    response: Response,
    settings: Settings,
    client: AuthClient,
) -> AuthSuccess:
    return await _sign_in("register", body, response, settings, client)


@router.post("/login", response_model=AuthSuccess)
async def login(
    body: LoginRequest,
    response: Response,
    settings: Settings,
    client: AuthClient,
) -> AuthSuccess:
    return await _sign_in("login", body, response, settings, client)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, settings: Settings) -> Response:
    _clear_auth_cookie(response, settings)
    return response


@router.get("/me", response_model=MeResponse)
async def me(user_id: UserId, settings: Settings, client: AuthClient) -> MeResponse:
    upstream = await _call_auth(
        client, settings, "get", "/internal/v1/auth/me", user_id=user_id
    )
    return _parse_upstream(upstream, MeResponse)


@router.patch("/me/settings", response_model=MeResponse)
async def patch_settings(
    body: SettingsPatch,
    user_id: UserId,
    settings: Settings,
    client: AuthClient,
) -> MeResponse:
    upstream = await _call_auth(
        client,
        settings,
        "patch",
        "/internal/v1/auth/me/settings",
        user_id=user_id,
        json=body.model_dump(mode="json", exclude_unset=True),
    )
    return _parse_upstream(upstream, MeResponse)
