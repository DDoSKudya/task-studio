from __future__ import annotations

import re

import httpx

_HTML_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_CLOUDFLARE_CODES = {
    520: "web server returned an unknown error",
    521: "web server is down",
    522: "connection timed out",
    523: "origin is unreachable",
    524: "a timeout occurred",
}


def enrich_provider_hint(detail: str) -> str:
    text = detail.strip()
    if not text:
        return text
    lower = text.casefold()
    cursor_markers = (
        "cloud agent",
        "usage-based pricing",
        "on-demand usage",
        "hard limit",
        "cursor-proxy",
        "background agent",
    )
    if any(marker in lower for marker in cursor_markers):
        return (
            f"{text} "
            "Task Studio Cursor mode uses Cloud Agents via cursor-proxy. "
            "Enable on-demand usage in the Cursor dashboard, "
            "or switch Tutor provider to Ollama in Settings."
        )
    mistral_rate_limit = (
        '"code":"1300"',
        '"code": 1300',
        'code":1300',
        "rate_limited",
        "rate limit exceeded",
    )
    if any(marker in lower for marker in mistral_rate_limit) or (
        "429" in lower and "rate" in lower
    ):
        return (
            f"{text} "
            "Бесплатный ключ Mistral имеет жёсткие лимиты запросов. "
            "Подождите 1–2 минуты и нажмите «Возобновить генерацию», "
            "либо переключитесь на Ollama (локально) в Настройках."
        )
    openai_capacity = (
        "service tier capacity exceeded",
        "request_tier_capacity_exceeded",
        '"code":"3505"',
        '"code": 3505',
        'code":3505',
    )
    if any(marker in lower for marker in openai_capacity) or (
        "429" in lower and "capacity" in lower
    ):
        return (
            f"{text} "
            "Это лимит ёмкости тарифа OpenAI (не «закончились токены»). "
            "Подождите 1–15 минут и повторите, уменьшите число слайдов/параллельность, "
            "проверьте Usage limits в OpenAI Platform, либо смените модель/тариф."
        )
    if any(
        marker in lower
        for marker in (
            "520",
            "521",
            "522",
            "523",
            "524",
            "cloudflare",
            "web server is returning an unknown error",
        )
    ):
        if "retry" in lower or "повтор" in lower:
            return text
        return (
            f"{text} "
            "Временный сбой у провайдера (часто Cloudflare). "
            "Подождите минуту и нажмите «Возобновить», либо смените провайдера в Настройках."
        )
    return text


def sanitize_provider_error_body(text: str, *, status_code: int | None = None) -> str:
    """Turn HTML gateway pages into a short human message."""
    stripped = (text or "").strip()
    if not stripped:
        return f"LLM HTTP {status_code}" if status_code else "LLM request failed"

    lower = stripped.casefold()
    looks_html = (
        "<html" in lower or "<!doctype" in lower or "<title>" in lower or "cloudflare" in lower
    )
    if not looks_html:
        return stripped[:500]

    title = ""
    if match := _HTML_TITLE_RE.search(stripped):
        title = " ".join(match.group(1).split())
    code = status_code
    if code is None:
        for candidate in _CLOUDFLARE_CODES:
            if str(candidate) in title or str(candidate) in stripped[:300]:
                code = candidate
                break
    label = _CLOUDFLARE_CODES.get(code or 0, "gateway error")
    if title and len(title) < 160:
        base = f"LLM provider unavailable (HTTP {code or 'error'}): {title}"
    else:
        base = f"LLM provider unavailable (HTTP {code or 'error'}): {label}"
    return base[:500]


def llm_http_error_message(exc: BaseException) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        status_code = response.status_code
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
        if raw := (response.text or "").strip():
            return enrich_provider_hint(sanitize_provider_error_body(raw, status_code=status_code))
        return f"LLM HTTP {status_code}"

    text = str(exc).strip()
    if not text:
        return "LLM request failed"
    return enrich_provider_hint(sanitize_provider_error_body(text)[:500])
