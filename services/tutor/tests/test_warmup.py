from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_is_cursor_provider_detects_proxy_url() -> None:
    warmup = load_service_module("app.domain.warmup")
    assert warmup.is_cursor_provider("http://cursor-proxy:8015/v1")
    assert warmup.is_cursor_provider("http://CURSOR-PROXY:8015/v1")
    assert not warmup.is_cursor_provider("http://ollama:11434/v1")
    assert not warmup.is_cursor_provider(None)
    assert not warmup.is_cursor_provider("")
