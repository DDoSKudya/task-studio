from __future__ import annotations

from app.config import clamp_presign_ttl_seconds, load_settings


def test_clamp_presign_ttl_seconds_bounds() -> None:
    assert clamp_presign_ttl_seconds(30) == 60
    assert clamp_presign_ttl_seconds(900) == 900
    assert clamp_presign_ttl_seconds(3600) == 900


def test_load_settings_default_presign_ttl(monkeypatch) -> None:
    monkeypatch.delenv("MINIO_PRESIGN_TTL_SECONDS", raising=False)
    settings = load_settings()
    assert settings.presign_ttl_seconds == 900


def test_load_settings_clamps_high_presign_ttl(monkeypatch) -> None:
    monkeypatch.setenv("MINIO_PRESIGN_TTL_SECONDS", "7200")
    settings = load_settings()
    assert settings.presign_ttl_seconds == 900
