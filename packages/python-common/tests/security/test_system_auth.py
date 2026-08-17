from __future__ import annotations

import os

import pytest
from fastapi import HTTPException
from studio_common.security.system_auth import (
    allow_insecure_defaults,
    require_system_token,
    resolve_jwt_secret,
    system_token_headers,
    verify_system_token,
)


def test_require_system_token_rejects_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_SYSTEM_TOKEN", "expected-token")
    with pytest.raises(HTTPException) as exc:
        require_system_token(None)
    assert exc.value.status_code == 401


def test_require_system_token_accepts_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_SYSTEM_TOKEN", "expected-token")
    require_system_token("expected-token")


def test_verify_allows_empty_when_insecure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_SYSTEM_TOKEN", "")
    monkeypatch.setenv("ALLOW_INSECURE_DEFAULTS", "1")
    verify_system_token(None)


def test_verify_rejects_empty_when_secure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALLOW_INSECURE_DEFAULTS", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ORCHESTRATOR_SYSTEM_TOKEN", "")
    with pytest.raises(HTTPException) as exc:
        verify_system_token(None)
    assert exc.value.status_code == 503


def test_resolve_jwt_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALLOW_INSECURE_DEFAULTS", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        resolve_jwt_secret("dev-only-change-me")


def test_resolve_jwt_allows_insecure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_INSECURE_DEFAULTS", "1")
    assert resolve_jwt_secret("dev-only-change-me") == "dev-only-change-me"
    assert allow_insecure_defaults() is True


def test_system_token_headers() -> None:
    os.environ["ORCHESTRATOR_SYSTEM_TOKEN"] = "abc"
    assert system_token_headers() == {"X-System-Token": "abc"}
    del os.environ["ORCHESTRATOR_SYSTEM_TOKEN"]
