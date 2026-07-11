from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL is required for auth integration tests",
)


@pytest.fixture
async def auth_client(build_app) -> AsyncGenerator[AsyncClient, None]:
    app = build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_register_and_login(auth_client: AsyncClient) -> None:
    email = f"user-{uuid.uuid4()}@example.com"
    password = "secure-pass-1"

    register = await auth_client.post(
        "/internal/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register.status_code == 201

    login = await auth_client.post(
        "/internal/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == email


@pytest.mark.asyncio
async def test_users_do_not_share_profiles(auth_client: AsyncClient) -> None:
    first_email = f"first-{uuid.uuid4()}@example.com"
    second_email = f"second-{uuid.uuid4()}@example.com"
    password = "secure-pass-1"

    first = await auth_client.post(
        "/internal/v1/auth/register",
        json={"email": first_email, "password": password},
    )
    second = await auth_client.post(
        "/internal/v1/auth/register",
        json={"email": second_email, "password": password},
    )
    first_id = first.json()["user"]["id"]
    second_id = second.json()["user"]["id"]

    first_me = await auth_client.get("/internal/v1/auth/me", headers={"X-User-Id": first_id})
    second_me = await auth_client.get("/internal/v1/auth/me", headers={"X-User-Id": second_id})

    assert first_me.json()["user"]["email"] == first_email
    assert second_me.json()["user"]["email"] == second_email
    assert first_me.json()["user"]["id"] != second_me.json()["user"]["id"]
