from __future__ import annotations

from collections.abc import Mapping, MutableMapping

from studio_common.secrets.secrets_crypto import INTEGRATION_SECRET_FIELDS

_REDACTED = "***"
_EXTRA_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set_cookie",
        "jwt_secret",
        "secrets_master_key",
        "master_key",
        "private_key",
    }
)
_SENSITIVE_SUFFIXES = (
    "_password",
    "_secret",
    "_token",
    "_api_key",
    "_encrypted",
)


def key_looks_sensitive(key: str) -> bool:
    lower = key.casefold().replace("-", "_")
    if lower in INTEGRATION_SECRET_FIELDS or lower in _EXTRA_SENSITIVE_KEYS:
        return True
    return lower.endswith(_SENSITIVE_SUFFIXES)


def redact_value(key: str, value: object) -> object:
    if key_looks_sensitive(key):
        if value is None or value == "":
            return value
        return _REDACTED
    if isinstance(value, Mapping):
        return {
            str(child_key): redact_value(str(child_key), child)
            for child_key, child in value.items()
        }
    if isinstance(value, list):
        return [redact_value(key, item) for item in value]
    return value


def redact_log_event(
    _logger: object,
    _method_name: str,
    event_dict: MutableMapping[str, object],
) -> Mapping[str, object]:
    for key in list(event_dict):
        event_dict[key] = redact_value(str(key), event_dict[key])
    return event_dict
