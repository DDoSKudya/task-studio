from __future__ import annotations

from typing import Literal

from studio_common.secrets.secrets_crypto import encrypt_secret_value
from studio_common.secrets.secrets_platform import decrypt_platform_credentials, merge_platform

__all__ = [
    "merge_tutor_settings",
    "merge_integrations_settings",
    "decrypt_platform_credentials",
    "merge_platform",
]

_TutorMode = Literal["ollama", "external", "cursor"]
_TUTOR_MODES: tuple[_TutorMode, ...] = ("ollama", "external", "cursor")
_PROFILE_KEYS = ("provider_url", "api_key_encrypted", "model")


def _infer_provider(provider_url: object) -> _TutorMode:
    if not isinstance(provider_url, str) or not provider_url.strip():
        return "ollama"
    cleaned = provider_url.strip().casefold()
    if "cursor-proxy" in cleaned:
        return "cursor"
    return "external"


def _coerce_profile(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, object] = {}
    for key in _PROFILE_KEYS:
        if key not in raw:
            continue
        value = raw[key]
        if key == "provider_url" and value is None:
            out[key] = None
        elif isinstance(value, str):
            out[key] = value.strip() if key != "provider_url" else value.strip() or None
    return out


def _apply_api_key(
    profile: dict[str, object],
    *,
    api_key: object,
    existing_encrypted: str | None,
    master_key: str | None,
) -> None:
    if isinstance(api_key, str) and api_key.strip():
        if encrypted := encrypt_secret_value(api_key, master_key=master_key):
            profile["api_key_encrypted"] = encrypted
        elif existing_encrypted:
            profile["api_key_encrypted"] = existing_encrypted
    elif existing_encrypted:
        profile["api_key_encrypted"] = existing_encrypted


def _load_existing_profiles(existing: dict[str, object] | None) -> dict[str, dict[str, object]]:
    profiles: dict[str, dict[str, object]] = {mode: {} for mode in _TUTOR_MODES}
    if not isinstance(existing, dict):
        return profiles

    raw_profiles = existing.get("provider_profiles")
    if isinstance(raw_profiles, dict):
        for mode in _TUTOR_MODES:
            profiles[mode] = _coerce_profile(raw_profiles.get(mode))

    legacy_mode = _infer_provider(existing.get("provider_url"))
    legacy = _coerce_profile(
        {
            "provider_url": existing.get("provider_url"),
            "api_key_encrypted": existing.get("api_key_encrypted"),
            "model": existing.get("model"),
        }
    )
    if legacy and not profiles[legacy_mode]:
        profiles[legacy_mode] = legacy
    return profiles


def merge_tutor_settings(
    incoming: dict[str, object],
    existing: dict[str, object] | None,
    *,
    master_key: str | None,
) -> dict[str, object]:
    merged = dict(incoming)
    top_level_api_key = merged.pop("api_key", None)

    active = merged.get("active_provider")
    if not isinstance(active, str) or active not in _TUTOR_MODES:
        active = _infer_provider(merged.get("provider_url"))
    merged["active_provider"] = active

    profiles = _load_existing_profiles(existing)
    incoming_profiles = merged.pop("provider_profiles", None)
    if isinstance(incoming_profiles, dict):
        for mode in _TUTOR_MODES:
            raw_profile = incoming_profiles.get(mode)
            if not isinstance(raw_profile, dict):
                continue
            current = dict(profiles.get(mode, {}))
            patch = _coerce_profile(raw_profile)
            for key in ("provider_url", "model"):
                if key in patch:
                    current[key] = patch[key]
            profile_key = raw_profile.get("api_key")
            existing_encrypted = current.get("api_key_encrypted")
            if isinstance(existing_encrypted, str):
                pass
            elif isinstance(profiles.get(mode, {}).get("api_key_encrypted"), str):
                existing_encrypted = str(profiles[mode]["api_key_encrypted"])
            else:
                existing_encrypted = None
            _apply_api_key(
                current,
                api_key=profile_key,
                existing_encrypted=existing_encrypted,
                master_key=master_key,
            )
            profiles[mode] = current

    active_profile = dict(profiles.get(active, {}))
    if "provider_url" in merged:
        active_profile["provider_url"] = merged.get("provider_url")
    if "model" in merged:
        active_profile["model"] = merged.get("model")
    existing_encrypted = active_profile.get("api_key_encrypted")
    if not isinstance(existing_encrypted, str):
        existing_encrypted = None
    _apply_api_key(
        active_profile,
        api_key=top_level_api_key,
        existing_encrypted=existing_encrypted,
        master_key=master_key,
    )
    profiles[active] = active_profile

    merged["provider_profiles"] = profiles
    merged["provider_url"] = active_profile.get("provider_url")
    merged["api_key_encrypted"] = active_profile.get("api_key_encrypted")
    merged["model"] = active_profile.get("model")
    return merged


def merge_integrations_settings(
    incoming: dict[str, object],
    existing: dict[str, object] | None,
    *,
    master_key: str | None,
) -> dict[str, object]:
    existing_map = existing if isinstance(existing, dict) else {}
    out: dict[str, object] = {}
    for platform_id, raw in incoming.items():
        if not isinstance(platform_id, str):
            continue
        if not isinstance(raw, dict):
            continue
        prev = existing_map.get(platform_id)
        prev_platform = prev if isinstance(prev, dict) else {}
        out[platform_id] = merge_platform(
            raw,
            prev_platform,
            master_key=master_key,
        )

    for platform_id, prev in existing_map.items():
        if platform_id not in out and isinstance(prev, dict):
            out[platform_id] = dict(prev)
    return out
