from __future__ import annotations

import httpx
from app.domain.llm.errors import llm_http_error_message


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
