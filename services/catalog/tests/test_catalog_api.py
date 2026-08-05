from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from studio_contracts.fixtures import build_sample_pack_bytes

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL is required for catalog integration tests",
)


@pytest.fixture
async def catalog_client(build_app, tmp_path) -> AsyncGenerator[AsyncClient, None]:
    app = build_app()
    app.state.catalog_settings = app.state.catalog_settings.__class__(
        packs_root=tmp_path / "packs",
        max_upload_bytes=10 * 1024 * 1024,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_upload_and_list_pack(catalog_client: AsyncClient) -> None:
    user_id = str(uuid.uuid4())
    headers = {"X-User-Id": user_id}

    upload = await catalog_client.post(
        "/internal/v1/catalog/packs/upload",
        headers=headers,
        files={"pack": ("sample.studio-pack", build_sample_pack_bytes(), "application/zip")},
    )
    assert upload.status_code == 201

    listed = await catalog_client.get("/internal/v1/catalog/packs", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["slug"] == "intro-python"
    assert body[0]["integrity"] == "ok"
    assert body[0]["integrity_issues"] == []


@pytest.mark.asyncio
async def test_users_do_not_share_catalog(catalog_client: AsyncClient) -> None:
    first_id = str(uuid.uuid4())
    second_id = str(uuid.uuid4())
    archive = build_sample_pack_bytes()

    created = await catalog_client.post(
        "/internal/v1/catalog/packs/upload",
        headers={"X-User-Id": first_id},
        files={"pack": ("sample.studio-pack", archive, "application/zip")},
    )
    assert created.status_code == 201

    first_list = await catalog_client.get(
        "/internal/v1/catalog/packs",
        headers={"X-User-Id": first_id},
    )
    second_list = await catalog_client.get(
        "/internal/v1/catalog/packs",
        headers={"X-User-Id": second_id},
    )
    assert len(first_list.json()) == 1
    assert second_list.json() == []


@pytest.mark.asyncio
async def test_delete_pack(catalog_client: AsyncClient) -> None:
    user_id = str(uuid.uuid4())
    headers = {"X-User-Id": user_id}

    created = await catalog_client.post(
        "/internal/v1/catalog/packs/upload",
        headers=headers,
        files={"pack": ("sample.studio-pack", build_sample_pack_bytes(), "application/zip")},
    )
    assert created.status_code == 201

    listed_before = await catalog_client.get("/internal/v1/catalog/packs", headers=headers)
    listed_body_before = listed_before.json()
    assert listed_before.status_code == 200
    assert len(listed_body_before) == 1

    pack_id = listed_body_before[0]["id"]

    deleted = await catalog_client.delete(f"/internal/v1/catalog/packs/{pack_id}", headers=headers)
    assert deleted.status_code == 204

    listed_after = await catalog_client.get("/internal/v1/catalog/packs", headers=headers)
    assert listed_after.status_code == 200
    assert listed_after.json() == []
