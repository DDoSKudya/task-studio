from __future__ import annotations

import httpx


class CursorApiError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def json_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def basic_auth(api_key: str) -> httpx.BasicAuth:

    return httpx.BasicAuth(api_key, "")


def error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text[:500] if text else f"HTTP {response.status_code}"
    if isinstance(payload, dict):
        for key in ("message", "error", "detail"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                nested = value.get("message")
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()

        code = payload.get("code")
        if isinstance(code, str) and code.strip():
            return f"{code}: {payload}"
    return f"HTTP {response.status_code}"


def model_ids_from_payload(payload: object) -> list[str]:
    ids: list[str] = ["auto"]
    items = payload.get("items") if isinstance(payload, dict) else None
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            model_id = item.get("id")
            if isinstance(model_id, str) and model_id.strip():
                ids.append(model_id.strip())
            aliases = item.get("aliases")
            if isinstance(aliases, list):
                for alias in aliases:
                    if isinstance(alias, str) and alias.strip():
                        ids.append(alias.strip())
    seen: set[str] = set()
    ordered: list[str] = []
    for model_id in ids:
        if model_id in seen:
            continue
        seen.add(model_id)
        ordered.append(model_id)
    return ordered
