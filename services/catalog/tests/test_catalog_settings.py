from __future__ import annotations

from app.config import load_settings


def test_load_settings_defaults_when_pack_max_empty(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PACKS_ROOT", str(tmp_path))
    monkeypatch.setenv("PACK_MAX_UPLOAD_MB", "")
    monkeypatch.delenv("MEDIA_SERVICE_URL", raising=False)
    settings = load_settings()
    assert settings.max_upload_bytes == 500 * 1024 * 1024


def test_load_settings_defaults_when_pack_max_invalid(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PACKS_ROOT", str(tmp_path))
    monkeypatch.setenv("PACK_MAX_UPLOAD_MB", "nope")
    settings = load_settings()
    assert settings.max_upload_bytes == 500 * 1024 * 1024


def test_load_settings_reads_pack_max(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PACKS_ROOT", str(tmp_path))
    monkeypatch.setenv("PACK_MAX_UPLOAD_MB", "12")
    settings = load_settings()
    assert settings.max_upload_bytes == 12 * 1024 * 1024


def test_load_settings_unset_pack_max_uses_default(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PACKS_ROOT", str(tmp_path))
    monkeypatch.delenv("PACK_MAX_UPLOAD_MB", raising=False)
    settings = load_settings()
    assert settings.max_upload_bytes == 500 * 1024 * 1024
    assert settings.packs_root == tmp_path
