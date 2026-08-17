from __future__ import annotations

import re

import httpx


def http_error_detail(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text[:400] if text else None
    if isinstance(payload, dict):
        for key in ("detail", "error", "message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        blob = str(payload)
        if "solve_sql" in blob or "invalid schema" in blob.casefold():
            if match := re.search(r"Reply has invalid schema:[^\"]+", blob):
                return match[0]
            return blob[:400]
    return None
