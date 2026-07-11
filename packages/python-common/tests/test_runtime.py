from __future__ import annotations

import pytest
from studio_common.runtime import bind_host


def test_bind_host_defaults_to_all_interfaces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOST", raising=False)
    assert bind_host() == "0.0.0.0"


def test_bind_host_uses_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOST", "127.0.0.1")
    assert bind_host() == "127.0.0.1"
