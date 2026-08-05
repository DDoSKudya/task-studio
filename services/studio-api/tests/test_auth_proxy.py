from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient, Response


@pytest.fixture
def jwt_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "dev-only-change-me-32-bytes-secret!")
    monkeypatch.setenv("JWT_EXPIRE_HOURS", "1")
    monkeypatch.setenv("AUTH_SERVICE_URL", "http://auth.test")
    monkeypatch.setenv("COOKIE_SECURE", "false")


@pytest.mark.asyncio
async def test_register_sets_auth_cookie(jwt_env: None, build_app) -> None:
    app = build_app()
    mock_client = AsyncMock()
    mock_client.post.return_value = Response(
        201,
        json={
            "user": {
                "id": "11111111-1111-1111-1111-111111111111",
                "email": "a@b.com",
                "locale": "en",
                "theme": "system",
            }
        },
    )
    app.state.upstream_client = mock_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/register",
            json={"email": "a@b.com", "password": "secure-pass"},
        )

    assert response.status_code == 201
    assert "studio_access_token" in response.cookies


@pytest.mark.asyncio
async def test_me_rotates_auth_cookie(jwt_env: None, build_app) -> None:
    from studio_common.jwt_tokens import create_access_token

    app = build_app()
    user_id = "11111111-1111-1111-1111-111111111111"
    mock_client = AsyncMock()
    mock_client.get.return_value = Response(
        200,
        json={
            "user": {
                "id": user_id,
                "email": "a@b.com",
                "locale": "en",
                "theme": "system",
            },
            "settings": {},
        },
    )
    app.state.upstream_client = mock_client
    token = create_access_token(
        user_id,
        secret="dev-only-change-me-32-bytes-secret!",
        expire_hours=1,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("studio_access_token", token)
        response = await client.get("/v1/auth/me")

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "studio_access_token=" in set_cookie
    assert "HttpOnly" in set_cookie


@pytest.mark.asyncio
async def test_me_requires_cookie(jwt_env: None, build_app) -> None:
    app = build_app()
    app.state.upstream_client = AsyncMock()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookie_with_204(jwt_env: None, build_app) -> None:
    app = build_app()
    app.state.upstream_client = AsyncMock()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("studio_access_token", "stale-token")
        response = await client.post("/v1/auth/logout")

    assert response.status_code == 204

    assert "studio_access_token" not in response.cookies or response.cookies.get(
        "studio_access_token"
    ) in {"", None}
