from __future__ import annotations

import uuid
from pathlib import Path

from app.domain.media.mirror import pack_archive_asset_id, zip_pack_directory


def test_pack_archive_asset_id_is_stable() -> None:
    pack_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    assert pack_archive_asset_id(pack_id, "1.0.0") == (
        "packs/11111111-1111-1111-1111-111111111111/1.0.0/archive.zip"
    )


def test_zip_pack_directory_includes_files(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    nested = tmp_path / "assets"
    nested.mkdir()
    (nested / "a.txt").write_text("hello", encoding="utf-8")
    payload = zip_pack_directory(tmp_path)
    assert payload[:2] == b"PK"
    assert len(payload) > 20
