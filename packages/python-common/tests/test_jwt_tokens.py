from __future__ import annotations

import uuid

import pytest
from studio_common.jwt_tokens import create_access_token, decode_user_id


def test_access_token_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "dev-only-change-me-32-bytes-secret!")
    monkeypatch.setenv("JWT_EXPIRE_HOURS", "1")
    user_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    token = create_access_token(str(user_id))
    assert decode_user_id(token) == user_id
