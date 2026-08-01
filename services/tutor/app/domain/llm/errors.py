from __future__ import annotations

import httpx


def enrich_provider_hint(detail: str) -> str:
    text = detail.strip()
    if not text:
        return text
    lower = text.casefold()
    markers = (
        "cloud agent",
        "usage-based pricing",
        "on-demand usage",
        "hard limit",
    )
    if any(marker in lower for marker in markers):
        return (
            f"{text} "
            "Task Studio Cursor mode uses Cloud Agents via cursor-proxy. "
            "Enable on-demand usage in the Cursor dashboard, "
            "or switch Tutor provider to Ollama in Settings."
        )
    return text


def llm_http_error_message(exc: BaseException) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            detail = payload.get("detail")
            if isinstance(detail, dict) and (
                nested := detail.get("message") or detail.get("detail")
            ):
                return enrich_provider_hint(str(nested).strip()[:500])
            if detail:
                return enrich_provider_hint(str(detail).strip()[:500])
            error = payload.get("error")
            if isinstance(error, dict) and (message := error.get("message")):
                return enrich_provider_hint(str(message).strip()[:500])
            if isinstance(error, str) and error.strip():
                return enrich_provider_hint(error.strip()[:500])
        if text := (response.text or "").strip():
            return enrich_provider_hint(text[:500])
        return f"LLM HTTP {response.status_code}"
    if not (text := str(exc).strip()):
        return "LLM request failed"
    return enrich_provider_hint(text[:500])
