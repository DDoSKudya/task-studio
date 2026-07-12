from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_system_prompt_replaces_placeholders() -> None:
    prompts = load_service_module("app.domain.prompts")
    prompt = prompts.system_prompt_for_phase("study", step_kind="code", step_title="Sum")
    assert "code" in prompt
    assert "Sum" in prompt


def test_system_prompt_for_study_phase() -> None:
    prompts = load_service_module("app.domain.prompts")
    prompt = prompts.system_prompt_for_phase("study", step_kind="theory", step_title="Hello")
    assert "study" in prompt.lower()
    assert "Hello" in prompt


def test_system_prompt_for_practice_phase() -> None:
    prompts = load_service_module("app.domain.prompts")
    prompt = prompts.system_prompt_for_phase("practice", step_kind="code", step_title="Sum")
    assert "practice" in prompt.lower()
    assert "Sum" in prompt
