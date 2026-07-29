from __future__ import annotations

from typing import Literal, assert_never

import httpx
from app.config import StudioApiSettings
from app.upstream import parse_upstream
from fastapi import Response
from studio_common.auth_schemas import AuthSuccess, LoginRequest, RegisterRequest

type AuthAction = Literal["register", "login"]
type AuthHttpMethod = Literal["get", "post", "patch"]


async def call_auth(
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


def set_auth_cookie(response: Response, token: str, settings: StudioApiSettings) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_hours * 3600,
        path="/",
    )


def clear_auth_cookie(response: Response, settings: StudioApiSettings) -> None:
    response.delete_cookie(key=settings.cookie_name, path="/")


def issue_session(
    response: Response,
    body: AuthSuccess,
    settings: StudioApiSettings,
) -> AuthSuccess:
    from studio_common.jwt_tokens import create_access_token

    token = create_access_token(
        body.user.id,
        secret=settings.jwt_secret,
        expire_hours=settings.jwt_expire_hours,
    )
    set_auth_cookie(response, token, settings)
    return body


async def sign_in(
    action: AuthAction,
    body: RegisterRequest | LoginRequest,
    response: Response,
    settings: StudioApiSettings,
    client: httpx.AsyncClient,
) -> AuthSuccess:
    upstream = await call_auth(
        client,
        settings,
        "post",
        f"/internal/v1/auth/{action}",
        json=body.model_dump(mode="json"),
    )
    auth = parse_upstream(upstream, AuthSuccess)
    return issue_session(response, auth, settings)
