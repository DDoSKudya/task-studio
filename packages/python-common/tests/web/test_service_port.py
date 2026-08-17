from __future__ import annotations

import pytest
from studio_common.web.app import service_port


def test_service_port_uses_default_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORT", raising=False)
    assert service_port(8001) == 8001


def test_service_port_uses_env_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "9000")
    assert service_port(8001) == 9000


def test_service_port_rejects_non_integer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "not-a-port")
    with pytest.raises(ValueError):
        service_port(8001)


def test_service_port_accepts_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "0")
    assert service_port(8001) == 0
