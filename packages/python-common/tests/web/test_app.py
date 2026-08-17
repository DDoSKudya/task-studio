from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from studio_common.web.app import create_service_app

SERVICE_NAMES = [
    "studio-api",
    "auth",
    "catalog",
    "sessions",
    "grading",
    "integrations",
    "tutor",
    "search",
    "analytics",
    "media",
    "lab-runner",
    "orchestrator",
]


@asynccontextmanager
async def service_client(service_name: str) -> AsyncIterator[AsyncClient]:
    app = create_service_app(service_name)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
@pytest.mark.parametrize("service_name", SERVICE_NAMES)
async def test_health(service_name: str) -> None:
    async with service_client(service_name) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_without_database() -> None:
    async with service_client("test-service") as client:
        response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_request_id_header() -> None:
    async with service_client("test-service") as client:
        response = await client.get("/health", headers={"X-Request-Id": "trace-42"})
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "trace-42"
