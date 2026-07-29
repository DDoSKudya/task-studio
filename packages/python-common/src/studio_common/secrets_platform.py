from __future__ import annotations

from studio_common.secrets_crypto import (
    INTEGRATION_SECRET_FIELDS,
    decrypt_secret_value,
    encrypt_secret_value,
)


def decrypt_platform_credentials(
    platform: dict[str, object],
    *,
    master_key: str | None,
) -> dict[str, str]:
                                                                                        
    out: dict[str, str] = {}
    for key, value in platform.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value.strip():
            continue
        if key.endswith("_encrypted"):
            plain_name = key[: -len("_encrypted")]
            if decrypted := decrypt_secret_value(value, master_key=master_key):
                out[plain_name] = decrypted
            continue
        if key in INTEGRATION_SECRET_FIELDS:
                                                                
            out[key] = value.strip()
            continue
        out[key] = value.strip()
    return out


def merge_platform(
    incoming: dict[str, object],
    existing: dict[str, object],
    *,
    master_key: str | None,
) -> dict[str, object]:
    merged: dict[str, object] = {}
                                                               
    for key, value in incoming.items():
        if not isinstance(key, str):
            continue
        if key.endswith("_encrypted"):
            continue
        if key in INTEGRATION_SECRET_FIELDS:
            continue
        if isinstance(value, str) and value.strip():
            merged[key] = value.strip()

    for field in INTEGRATION_SECRET_FIELDS:
        plain = incoming.get(field)
        if isinstance(plain, str) and plain.strip():
            if encrypted := encrypt_secret_value(plain, master_key=master_key):
                merged[f"{field}_encrypted"] = encrypted
            elif isinstance(existing.get(f"{field}_encrypted"), str):
                merged[f"{field}_encrypted"] = existing[f"{field}_encrypted"]
            else:
                                                                               
                merged[field] = plain.strip()
            continue
        enc_key = f"{field}_encrypted"
        prev_enc = existing.get(enc_key)
        if isinstance(prev_enc, str) and prev_enc.strip():
            merged[enc_key] = prev_enc
            continue
        prev_plain = existing.get(field)
        if isinstance(prev_plain, str) and prev_plain.strip():
            if encrypted := encrypt_secret_value(
                prev_plain, master_key=master_key
            ):
                merged[enc_key] = encrypted
            else:
                merged[field] = prev_plain.strip()

                                                                             
    for key, value in existing.items():
        if key in merged or key in INTEGRATION_SECRET_FIELDS:
            continue
        if key.endswith("_encrypted"):
                                                                
            plain = key[: -len("_encrypted")]
            if plain in INTEGRATION_SECRET_FIELDS:
                continue
        if isinstance(value, str) and value.strip() and key not in merged:
            merged[key] = value
    return merged
