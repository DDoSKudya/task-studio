from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_model_aliases_match_latest_tag() -> None:
    status = load_service_module("app.domain.status")
    installed = ["llama3.2:latest", "qwen2:0.5b"]
    assert status.model_is_available("llama3.2", installed)
    assert status.model_is_available("llama3.2:latest", installed)
    assert not status.model_is_available("mistral", installed)
    assert status.resolve_installed_model("llama3.2", installed) == "llama3.2:latest"
    assert status.resolve_installed_model("", installed) == "llama3.2:latest"
