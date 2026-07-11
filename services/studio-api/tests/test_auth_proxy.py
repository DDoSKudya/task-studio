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
    app.state.auth_client = mock_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/register",
            json={"email": "a@b.com", "password": "secure-pass"},
        )

    assert response.status_code == 201
    assert "studio_access_token" in response.cookies


@pytest.mark.asyncio
async def test_me_requires_cookie(jwt_env: None, build_app) -> None:
    app = build_app()
    app.state.auth_client = AsyncMock()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/auth/me")
    assert response.status_code == 401
