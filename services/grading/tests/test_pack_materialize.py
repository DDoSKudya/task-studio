from __future__ import annotations

import io
import zipfile
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from app.config import GradingSettings
from app.domain.pack.materialize import ensure_local_pack_root


def _settings(tmp_path: Path) -> GradingSettings:
    return GradingSettings(
        piston_url="http://piston",
        piston_timeout_seconds=1.0,
        rabbitmq_url="",
        grading_jobs_queue="g",
        lab_jobs_queue="l",
        catalog_service_url="http://catalog",
        sessions_service_url="http://sessions",
        auth_service_url="http://auth",
        tutor_service_url="http://tutor",
        media_service_url="http://media",
        packs_root=str(tmp_path),
        llm_grade_enabled=True,
        llm_grade_min_confidence=0.65,
        secrets_master_key=None,
    )


@pytest.mark.asyncio
async def test_ensure_local_pack_root_uses_existing_disk(tmp_path: Path) -> None:
    pack_id = uuid4()
    disk = tmp_path / "existing"
    disk.mkdir()
    (disk / "manifest.json").write_text("{}", encoding="utf-8")
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    async with httpx.AsyncClient(transport=transport) as client:
        root = await ensure_local_pack_root(
            client,
            _settings(tmp_path),
            user_id=uuid4(),
            pack_id=pack_id,
            version="1.0.0",
            disk_path=disk,
            object_key="users/x/packs/y",
        )
    assert root == str(disk)


@pytest.mark.asyncio
async def test_ensure_local_pack_root_hydrates_from_media(tmp_path: Path) -> None:
    pack_id = UUID("11111111-1111-1111-1111-111111111111")
    user_id = UUID("22222222-2222-2222-2222-222222222222")
    missing = tmp_path / "missing-on-disk"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("manifest.json", "{}")
        archive.writestr("compose.yml", "services: {}\n")

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/internal/v1/media/packs/" in str(request.url)
        return httpx.Response(200, content=buf.getvalue())

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        root = await ensure_local_pack_root(
            client,
            _settings(tmp_path),
            user_id=user_id,
            pack_id=pack_id,
            version="1.0.0",
            disk_path=missing,
            object_key=f"users/{user_id}/packs/{pack_id}/1.0.0/archive.zip",
        )
    target = Path(root)
    assert target.is_dir()  # noqa: ASYNC240 — sync assert after await
    assert (target / "manifest.json").is_file()  # noqa: ASYNC240
    assert (target / "compose.yml").is_file()  # noqa: ASYNC240
