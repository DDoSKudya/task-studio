from __future__ import annotations

import pytest
from studio_common.migrations import _is_transient_db_error, upgrade_head


def test_connection_refused_is_transient() -> None:
    assert _is_transient_db_error(ConnectionRefusedError("db down"))


def test_value_error_is_not_transient() -> None:
    assert not _is_transient_db_error(ValueError("bad revision"))


@pytest.mark.asyncio
async def test_upgrade_head_retries_transient_then_succeeds(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_upgrade(_config, _rev: str) -> None:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionRefusedError("not ready")

    class FakeConfig:
        def __init__(self, _path: str) -> None:
            pass

    monkeypatch.setattr("studio_common.migrations.Config", FakeConfig)
    monkeypatch.setattr("studio_common.migrations.command.upgrade", fake_upgrade)
    monkeypatch.setattr("studio_common.migrations._TRANSIENT_WAIT_SEC", (0.01, 0.01, 0.01))

    await upgrade_head("alembic.ini")
    assert calls["n"] == 3
