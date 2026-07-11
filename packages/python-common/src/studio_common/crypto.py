from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_SIZE = 12
_KEY_SIZE = 32


def _decode_master_key(key_b64: str | None = None) -> bytes:
    raw = key_b64 if key_b64 is not None else os.environ["SECRETS_MASTER_KEY"]
    key = base64.b64decode(raw)
    if len(key) != _KEY_SIZE:
        msg = "SECRETS_MASTER_KEY must decode to 32 bytes"
        raise ValueError(msg)
    return key


def encrypt_bytes(plaintext: bytes, *, key_b64: str | None = None) -> bytes:
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = AESGCM(_decode_master_key(key_b64)).encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_bytes(payload: bytes, *, key_b64: str | None = None) -> bytes:
    if len(payload) <= _NONCE_SIZE:
        msg = "encrypted payload is too short"
        raise ValueError(msg)
    nonce = payload[:_NONCE_SIZE]
    ciphertext = payload[_NONCE_SIZE:]
    return AESGCM(_decode_master_key(key_b64)).decrypt(nonce, ciphertext, None)
