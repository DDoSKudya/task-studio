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
async def test_media_redirects_to_presigned_url(media_env: None, build_app) -> None:
    app = build_app()
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True
    mock_client.stat_object.return_value = None
    mock_client.presigned_get_object.return_value = "https://minio.test/studio/object"
    app.state.minio_client = mock_client

    transport = ASGITransport(app=app)
    user_id = "11111111-1111-1111-1111-111111111111"
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        response = await client.get(
            "/internal/v1/media/packs/demo.txt",
            headers={"X-User-Id": user_id},
        )

    assert response.status_code == 307
    assert response.headers["location"] == "https://minio.test/studio/object"
