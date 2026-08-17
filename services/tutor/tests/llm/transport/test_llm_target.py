from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_is_ollama_target_matches_configured_url() -> None:
    llm = load_service_module("app.domain.llm")
    config = load_service_module("app.config").load_config()
    ollama = llm.LlmTarget("http://ollama:11434/v1", None, config.ollama_model)
    external = llm.LlmTarget("https://api.mistral.ai/v1", "key", "mistral")
    cursor = llm.LlmTarget("http://cursor-proxy:8015/v1", "key", "auto")
    assert llm.is_ollama_target(config, ollama)
    assert not llm.is_ollama_target(config, external)
    assert llm.is_cursor_target(cursor)
    assert not llm.is_cursor_target(ollama)
    assert not llm.is_cursor_target(external)


def test_course_provider_url_ollama_mode_ignores_leftover_cloud() -> None:
    llm = load_service_module("app.domain.llm")
    config = load_service_module("app.config").load_config()
    assert (
        llm.course_provider_url(
            config,
            provider_url="https://api.openai.com/v1",
            active_provider="ollama",
        )
        is None
    )
    assert (
        llm.course_provider_url(
            config,
            provider_url="http://127.0.0.1:11434/v1",
            active_provider="cursor",
        )
        is None
    )
    cursor = "http://cursor-proxy:8015/v1"
    assert (
        llm.course_provider_url(
            config,
            provider_url=cursor,
            active_provider="cursor",
        )
        == cursor
    )
    cloud = "https://api.openai.com/v1"
    assert (
        llm.course_provider_url(
            config,
            provider_url=cloud,
            active_provider="external",
        )
        == cloud
    )


def test_resolve_cursor_target_uses_auto_model_and_long_read() -> None:
    llm = load_service_module("app.domain.llm")
    config = load_service_module("app.config").load_config()
    target = llm.resolve_llm_target(
        config,
        provider_url="http://cursor-proxy:8015/v1",
        api_key_encrypted=None,
        model=None,
    )
    assert target is not None
    assert target.model == "auto"
    assert target.read_timeout_seconds == 900.0
    assert llm.is_cursor_target(target)
    named = llm.resolve_llm_target(
        config,
        provider_url="http://cursor-proxy:8015/v1",
        api_key_encrypted=None,
        model="composer-1",
    )
    assert named is not None
    assert named.model == "composer-1"
    cloud = llm.resolve_llm_target(
        config,
        provider_url="https://api.openai.com/v1",
        api_key_encrypted=None,
        model="gpt-4o-mini",
    )
    assert cloud is not None
    assert cloud.model == "gpt-4o-mini"
    assert cloud.read_timeout_seconds is None
    assert not llm.is_cursor_target(cloud)


def test_resolve_llm_target_prefers_provider_url() -> None:
    llm = load_service_module("app.domain.llm")
    config = load_service_module("app.config").load_config()
    target = llm.resolve_llm_target(
        config,
        provider_url=None,
        api_key_encrypted=None,
        model=None,
    )
    assert target is not None
    assert target.base_url == "http://ollama:11434/v1"
    assert llm.is_ollama_target(config, target)
