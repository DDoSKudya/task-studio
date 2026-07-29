from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_is_ollama_target_matches_configured_url() -> None:
    llm = load_service_module("app.domain.llm")
    config_mod = load_service_module("app.config")
    config = config_mod.TutorConfig(
        auth_service_url="http://auth:8001",
        sessions_service_url="http://sessions:8003",
        ollama_url="http://ollama:11434",
        ollama_model="llama3.2",
        default_provider_url="",
        rate_limit_per_minute=30,
        secrets_master_key=None,
    )
    ollama = llm.LlmTarget("http://ollama:11434/v1", None, "llama3.2")
    external = llm.LlmTarget("https://api.mistral.ai/v1", "key", "mistral")
    cursor = llm.LlmTarget("http://cursor-proxy:8015/v1", "key", "auto")
    assert llm.is_ollama_target(config, ollama)
    assert not llm.is_ollama_target(config, external)
    assert llm.is_cursor_target(cursor)
    assert not llm.is_cursor_target(ollama)
    assert not llm.is_cursor_target(external)


def test_resolve_llm_target_prefers_provider_url() -> None:
    llm = load_service_module("app.domain.llm")
    config_mod = load_service_module("app.config")
    config = config_mod.TutorConfig(
        auth_service_url="http://auth:8001",
        sessions_service_url="http://sessions:8003",
        ollama_url="http://ollama:11434",
        ollama_model="llama3.2",
        default_provider_url="",
        rate_limit_per_minute=30,
        secrets_master_key=None,
    )
    target = llm.resolve_llm_target(
        config,
        provider_url=None,
        api_key_encrypted=None,
        model=None,
    )
    assert target is not None
    assert target.base_url == "http://ollama:11434/v1"
    assert llm.is_ollama_target(config, target)
