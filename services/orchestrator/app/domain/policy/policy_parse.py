from __future__ import annotations


def require_mapping(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key)
    if not isinstance(value, dict):
        msg = f"policies[{key!r}] must be a mapping"
        raise ValueError(msg)
    return value


def positive_int(raw: dict[str, object], key: str, *, default: int) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return default
    return value


def positive_float(raw: dict[str, object], key: str, *, default: float) -> float:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        return default
    return float(value)
