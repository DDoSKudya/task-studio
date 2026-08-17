from __future__ import annotations

import base64

from studio_common.security.crypto import decrypt_bytes, encrypt_bytes

INTEGRATION_SECRET_FIELDS = frozenset(
    {
        "password",
        "token",
        "api_key",
        "client_secret",
        "access_token",
        "refresh_token",
        "secret",
    }
)


def encrypt_secret_value(plaintext: str, *, master_key: str | None) -> str | None:
    if not plaintext.strip() or not master_key:
        return None
    encrypted = encrypt_bytes(plaintext.encode("utf-8"), key_b64=master_key)
    return base64.b64encode(encrypted).decode("ascii")


def decrypt_secret_value(encrypted_b64: str, *, master_key: str | None) -> str | None:
    if not encrypted_b64.strip() or not master_key:
        return None
    try:
        payload = base64.b64decode(encrypted_b64)
        return decrypt_bytes(payload, key_b64=master_key).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
