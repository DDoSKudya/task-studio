from __future__ import annotations

import base64
import os

from studio_common.secrets.secrets_settings import (
    decrypt_platform_credentials,
    merge_integrations_settings,
    merge_tutor_settings,
)


def _key() -> str:
    return base64.b64encode(os.urandom(32)).decode("ascii")


def test_merge_tutor_encrypts_and_preserves() -> None:
    key = _key()
    first = merge_tutor_settings(
        {"provider_url": "http://x", "api_key": "secret"},
        None,
        master_key=key,
    )
    assert "api_key" not in first
    assert isinstance(first.get("api_key_encrypted"), str)

    second = merge_tutor_settings(
        {"provider_url": "http://y", "model": "m"},
        first,
        master_key=key,
    )
    assert second["api_key_encrypted"] == first["api_key_encrypted"]
    assert second["provider_url"] == "http://y"


def test_merge_tutor_keeps_keys_per_provider() -> None:
    key = _key()
    saved = merge_tutor_settings(
        {
            "active_provider": "cursor",
            "provider_url": "http://cursor-proxy:8015/v1",
            "api_key": "cursor-secret",
            "model": "auto",
            "provider_profiles": {
                "external": {
                    "provider_url": "https://api.openai.com/v1",
                    "api_key": "openai-secret",
                    "model": "gpt-4o-mini",
                },
            },
        },
        None,
        master_key=key,
    )
    profiles = saved.get("provider_profiles")
    assert isinstance(profiles, dict)
    cursor_profile = profiles.get("cursor")
    external_profile = profiles.get("external")
    assert isinstance(cursor_profile, dict)
    assert isinstance(external_profile, dict)
    assert cursor_profile.get("api_key_encrypted")
    assert external_profile.get("api_key_encrypted")
    assert cursor_profile.get("api_key_encrypted") != external_profile.get("api_key_encrypted")

    switched = merge_tutor_settings(
        {
            "active_provider": "external",
            "provider_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
        },
        saved,
        master_key=key,
    )
    switched_profiles = switched.get("provider_profiles")
    assert isinstance(switched_profiles, dict)
    assert switched_profiles["cursor"].get("api_key_encrypted") == cursor_profile.get(
        "api_key_encrypted"
    )
    assert switched["api_key_encrypted"] == external_profile.get("api_key_encrypted")


def test_merge_integrations_encrypts_password() -> None:
    key = _key()
    saved = merge_integrations_settings(
        {"stepik": {"username": "u", "password": "p", "client_id": "c"}},
        None,
        master_key=key,
    )
    platform = saved["stepik"]
    assert isinstance(platform, dict)
    assert "password" not in platform
    assert "password_encrypted" in platform
    assert platform["username"] == "u"

    plain = decrypt_platform_credentials(platform, master_key=key)
    assert plain["password"] == "p"
    assert plain["username"] == "u"


def test_merge_integrations_preserves_secrets_when_omitted() -> None:
    key = _key()
    existing = merge_integrations_settings(
        {"stepik": {"username": "u", "password": "p"}},
        None,
        master_key=key,
    )
    updated = merge_integrations_settings(
        {"stepik": {"username": "u2"}},
        existing,
        master_key=key,
    )
    platform = updated["stepik"]
    assert isinstance(platform, dict)
    assert platform["username"] == "u2"
    plain = decrypt_platform_credentials(platform, master_key=key)
    assert plain["password"] == "p"


def test_decrypt_accepts_legacy_plaintext() -> None:
    plain = decrypt_platform_credentials(
        {"username": "u", "password": "legacy"},
        master_key=_key(),
    )
    assert plain == {"username": "u", "password": "legacy"}
