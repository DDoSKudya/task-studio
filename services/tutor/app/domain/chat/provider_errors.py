from __future__ import annotations

import json

import httpx
from app.domain.llm.errors import enrich_provider_hint


def provider_error_message(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        detail = str(exc).strip()
        return enrich_provider_hint(detail) or "LLM provider returned an error."
    if isinstance(exc, httpx.ConnectError):
        return (
            "Cannot reach the LLM provider. "
            "If you use Cursor, check that cursor-proxy is running "
            "and the provider URL is http://cursor-proxy:8015/v1."
        )
    if isinstance(exc, httpx.TimeoutException):
        return "LLM provider timed out. Try again, or switch model/provider."
    if isinstance(exc, httpx.HTTPStatusError):
        detail = http_error_detail(exc)
        status = exc.response.status_code
        if status in {401, 403}:
            return f"LLM auth failed (HTTP {status}). Check the API key in Settings."
        if detail:
            return enrich_provider_hint(f"LLM provider error (HTTP {status}): {detail}")
        return f"LLM provider error (HTTP {status})."
    return "Tutor is temporarily unavailable. Try static hints."


def http_error_detail(exc: httpx.HTTPStatusError) -> str:
    raw = ""
    if exc.args and isinstance(exc.args[0], str):
        candidate = exc.args[0].strip()

        if candidate and not candidate.startswith(("Client error", "Server error")):
            raw = candidate
    if not raw:
        raw = (exc.response.text or "").strip()
    if not raw:
        return ""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:280]
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()[:280]
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()[:280]
        if isinstance(error, str) and error.strip():
            return error.strip()[:280]
    return raw[:280]
