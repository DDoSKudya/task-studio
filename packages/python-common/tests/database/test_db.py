from __future__ import annotations

import pytest
from studio_common.database.db import create_engine

_DB_URL = "postgresql+asyncpg://studio:studio@localhost:5432/studio"


def test_create_engine_none_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert create_engine() is None


def test_create_engine_none_with_blank_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "   ")
    assert create_engine() is None


def test_create_engine_when_url_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", _DB_URL)
    assert create_engine() is not None
