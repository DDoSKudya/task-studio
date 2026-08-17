from __future__ import annotations

import base64

import pytest
from studio_common.security.crypto import decrypt_bytes, encrypt_bytes

_TEST_KEY = base64.b64encode(b"01234567890123456789012345678901").decode()


def test_encrypt_decrypt_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_MASTER_KEY", _TEST_KEY)
    plaintext = b"stepik-token"
    assert decrypt_bytes(encrypt_bytes(plaintext)) == plaintext


def test_decrypt_rejects_short_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRETS_MASTER_KEY", _TEST_KEY)
    with pytest.raises(ValueError, match="too short"):
        decrypt_bytes(b"short")
