from __future__ import annotations

import httpx
from app.domain.llm.errors import llm_http_error_message, sanitize_provider_error_body


def test_llm_http_error_message_reads_cursor_detail() -> None:
    request = httpx.Request("POST", "http://cursor-proxy:8015/v1/chat/completions")
    response = httpx.Response(
        400,
        request=request,
        json={
            "detail": (
                "Usage-based pricing required. Background Agent requires at least "
                "$2 remaining until your hard limit."
            )
        },
    )
    exc = httpx.HTTPStatusError("boom", request=request, response=response)
    message = llm_http_error_message(exc)
    assert "Usage-based pricing required" in message
    assert "Ollama" in message


def test_llm_http_error_message_cloud_agent_quota() -> None:
    request = httpx.Request("POST", "http://cursor-proxy:8015/v1/chat/completions")
    response = httpx.Response(
        429,
        request=request,
        json={
            "detail": (
                "You've used all included Cloud Agent usage: "
                "Enable on-demand usage to continue using Cloud Agents"
            )
        },
    )
    exc = httpx.HTTPStatusError("boom", request=request, response=response)
    message = llm_http_error_message(exc)
    assert "Cloud Agent usage" in message
    assert "on-demand" in message.casefold() or "Ollama" in message


def test_llm_http_error_message_falls_back_to_status() -> None:
    request = httpx.Request("POST", "http://ollama:11434/v1/chat/completions")
    response = httpx.Response(502, request=request, text="")
    exc = httpx.HTTPStatusError("boom", request=request, response=response)
    assert llm_http_error_message(exc) == "LLM HTTP 502"


def test_llm_http_error_message_openai_tier_capacity() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(
        429,
        request=request,
        json={
            "error": {
                "message": "Service tier capacity exceeded for this model.",
                "type": "request_tier_capacity_exceeded",
                "code": "3505",
            }
        },
    )
    exc = httpx.HTTPStatusError("boom", request=request, response=response)
    message = llm_http_error_message(exc)
    assert "capacity exceeded" in message.casefold()
    assert "openai" in message.casefold()
    assert "cursor" not in message.casefold()
    assert "токен" in message.casefold() or "тариф" in message.casefold()


def test_llm_http_error_message_sanitizes_cloudflare_520_html() -> None:
    request = httpx.Request("POST", "https://api.mistral.ai/v1/chat/completions")
    html = (
        "<!DOCTYPE html><html><head>"
        "<TITLE>MISTRAL.AI | 520: WEB SERVER IS RETURNING AN UNKNOWN ERROR</TITLE>"
        "</head><body>cloudflare</body></html>"
    )
    response = httpx.Response(520, request=request, text=html)
    exc = httpx.HTTPStatusError("boom", request=request, response=response)
    message = llm_http_error_message(exc)
    assert "<html" not in message.casefold()
    assert "520" in message
    assert "MISTRAL" in message.upper() or "unavailable" in message.casefold()
    assert "cloudflare" in message.casefold() or "провайдер" in message.casefold()


def test_sanitize_provider_error_body_keeps_plain_text() -> None:
    assert sanitize_provider_error_body('{"error":"nope"}') == '{"error":"nope"}'


def test_is_transient_includes_cloudflare_520() -> None:
    from app.domain.llm.transport.retry import is_transient_llm_error

    request = httpx.Request("POST", "https://api.mistral.ai/v1/chat/completions")
    response = httpx.Response(520, request=request, text="x")
    exc = httpx.HTTPStatusError("boom", request=request, response=response)
    assert is_transient_llm_error(exc)
