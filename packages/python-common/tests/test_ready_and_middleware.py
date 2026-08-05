from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from studio_common.app import create_service_app


@asynccontextmanager
async def service_client(service_name: str) -> AsyncIterator[AsyncClient]:
    app = create_service_app(service_name)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def _mock_session_factory(*, execute_raises: bool) -> MagicMock:
    mock_session = AsyncMock()
    if execute_raises:
        mock_session.execute.side_effect = SQLAlchemyError("connection failed")
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_session
    mock_context.__aexit__.return_value = None
    return MagicMock(return_value=mock_context)


@pytest.mark.asyncio
async def test_ready_degraded_when_database_ping_fails() -> None:
    app = create_service_app("test-service")
    app.state.db_session_factory = _mock_session_factory(execute_raises=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded"}


@pytest.mark.asyncio
async def test_ready_degraded_on_os_error() -> None:
    app = create_service_app("test-service")
    mock_session = AsyncMock()
    mock_session.execute.side_effect = OSError("connection refused")
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_session
    mock_context.__aexit__.return_value = None
    app.state.db_session_factory = MagicMock(return_value=mock_context)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded"}
    app = create_service_app("test-service")
    app.state.db_session_factory = _mock_session_factory(execute_raises=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_request_id_generated_when_header_missing() -> None:
    async with service_client("test-service") as client:
        response = await client.get("/health")
    uuid.UUID(response.headers["X-Request-Id"])


@pytest.mark.asyncio
async def test_request_id_generated_when_header_empty() -> None:
    async with service_client("test-service") as client:
        response = await client.get("/health", headers={"X-Request-Id": ""})
    request_id = response.headers["X-Request-Id"]
    assert request_id
    uuid.UUID(request_id)


@pytest.mark.asyncio
async def test_request_id_generated_when_header_whitespace() -> None:
    async with service_client("test-service") as client:
        response = await client.get("/health", headers={"X-Request-Id": "   "})
    request_id = response.headers["X-Request-Id"]
    assert request_id
    uuid.UUID(request_id)


@pytest.mark.asyncio
async def test_metrics_endpoint_available() -> None:
    async with service_client("test-service") as client:
        response = await client.get("/metrics")
    assert response.status_code == 200
    assert response.text
