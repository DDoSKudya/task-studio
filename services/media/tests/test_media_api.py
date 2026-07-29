from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def media_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIO_ENDPOINT", "minio.test:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "studio")
    monkeypatch.setenv("MINIO_SECRET_KEY", "studio-secret")


@pytest.mark.asyncio
async def test_media_streams_object_bytes(media_env: None, build_app) -> None:
    app = build_app()
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True
    mock_client.stat_object.return_value = None

    class _Resp:
        headers = {"Content-Type": "text/plain", "Content-Length": "5"}

        def stream(self, _chunk: int):
            yield b"hello"

        def close(self) -> None:
            return None

        def release_conn(self) -> None:
            return None

    mock_client.get_object.return_value = _Resp()
    app.state.minio_client = mock_client

    transport = ASGITransport(app=app)
    user_id = "11111111-1111-1111-1111-111111111111"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/internal/v1/media/packs/demo.txt",
            headers={"X-User-Id": user_id},
        )

    assert response.status_code == 200
    assert response.content == b"hello"
    assert response.headers["content-type"].startswith("text/plain")


@pytest.mark.asyncio
async def test_media_upload_puts_object(media_env: None, build_app) -> None:
    app = build_app()
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True
    mock_client.put_object.return_value = None
    app.state.minio_client = mock_client

    transport = ASGITransport(app=app)
    user_id = "11111111-1111-1111-1111-111111111111"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/internal/v1/media/upload",
            headers={"X-User-Id": user_id},
            files={"file": ("note.txt", b"hello media", "text/plain")},
            data={"asset_id": "notes/hello.txt"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["asset_id"] == "notes/hello.txt"
    assert body["size"] == 11
    mock_client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_media_delete_removes_object(media_env: None, build_app) -> None:
    app = build_app()
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True
    mock_client.remove_object.return_value = None
    app.state.minio_client = mock_client

    transport = ASGITransport(app=app)
    user_id = "11111111-1111-1111-1111-111111111111"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(
            "/internal/v1/media/notes/hello.txt",
            headers={"X-User-Id": user_id},
        )

    assert response.status_code == 204
    mock_client.remove_object.assert_called_once()
