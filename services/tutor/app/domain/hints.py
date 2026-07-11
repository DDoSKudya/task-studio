from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_RULES_PATH = Path(__file__).resolve().parents[2] / "hints" / "fallback_rules.json"


@lru_cache(maxsize=1)
def load_fallback_rules() -> dict[str, list[str]]:
    if not _RULES_PATH.is_file():
        return {}
    payload = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {
        key: [hint for hint in value if isinstance(hint, str)]
        for key, value in payload.items()
        if isinstance(key, str) and isinstance(value, list)
    }


def hints_for_kind(step_kind: str) -> list[str]:
    rules = load_fallback_rules()
    return list(rules.get(step_kind) or rules.get("theory", []))
