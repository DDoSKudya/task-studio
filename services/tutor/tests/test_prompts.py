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
    assert "Task Studio" in prompt
    assert "theory" in prompt.lower()
    assert "socratic" in prompt.lower()


def test_system_prompt_for_practice_phase() -> None:
    prompts = load_service_module("app.domain.prompts")
    prompt = prompts.system_prompt_for_phase("practice", step_kind="code", step_title="Sum")
    assert "practice" in prompt.lower()
    assert "Sum" in prompt
    assert "attempt" in prompt.lower() or "check" in prompt.lower()
    assert "verify" in prompt.lower()


def test_ollama_profile_adds_token_budget_and_quality() -> None:
    prompts = load_service_module("app.domain.prompts")
    prompt = prompts.system_prompt_for_phase(
        "practice",
        step_kind="code",
        step_title="Select",
        compact=True,
        sql_aware=True,
    )
    assert "token budget" in prompt.lower()
    assert "ollama" in prompt.lower() or "local model" in prompt.lower()
    assert "sql coach" in prompt.lower()
    assert "80 words" in prompt or "≤ 80" in prompt


def test_external_profile_uses_external_provider_block() -> None:
    prompts = load_service_module("app.domain.prompts")
    prompt = prompts.system_prompt_for_phase(
        "study",
        step_kind="theory",
        step_title="Intro",
        compact=False,
    )
    assert "external" in prompt.lower() or "strong api" in prompt.lower()
    assert "token budget" not in prompt.lower()


def test_hints_system_prompt_includes_kind_overlay() -> None:
    prompts = load_service_module("app.domain.prompts")
    prompt = prompts.hints_system_prompt(step_kind="quiz", step_title="Basics")
    assert "Basics" in prompt
    assert "quiz" in prompt.lower()
    assert "2 or 3" in prompt or "2-3" in prompt


def test_pack_studio_system_prompt_requires_json() -> None:
    prompts = load_service_module("app.domain.prompts")
    prompt = prompts.pack_studio_system_prompt()
    assert "JSON" in prompt
    assert "manifest" in prompt.lower()
    assert "socratic" not in prompt.lower()


def test_skills_for_matrix() -> None:
    prompts = load_service_module("app.domain.prompts")
    req = prompts.PromptRequest(
        mode="chat",
        phase="practice",
        step_kind="code",
        step_title="X",
        compact=True,
        sql_aware=True,
    )
    skills = prompts.skills_for(req)
    assert skills == [
        "socratic",
        "atypical-cases",
        "negative-constraints",
        "kind-code",
        "attempt-review",
        "verify-with-checks",
        "ground-on-page",
        "sql-coach",
        "token-budget",
    ]


def test_skills_for_external_practice_adds_light_cot() -> None:
    prompts = load_service_module("app.domain.prompts")
    req = prompts.PromptRequest(
        mode="chat",
        phase="practice",
        step_kind="quiz",
        step_title="Q",
        compact=False,
        sql_aware=False,
    )
    skills = prompts.skills_for(req)
    assert "light-cot" in skills
    assert "token-budget" not in skills


def test_format_learner_turn_has_sections() -> None:
    prompts = load_service_module("app.domain.prompts")
    text = prompts.format_learner_turn("Почему нужен JOIN?")
    assert "<learner_message>" in text
    assert "</learner_message>" in text
    assert "<response_contract>" in text
    assert "JOIN" in text


def test_negative_constraints_in_chat_and_course() -> None:
    prompts = load_service_module("app.domain.prompts")
    chat = prompts.PromptRequest(
        mode="chat",
        phase="study",
        step_kind="theory",
        step_title="T",
        compact=True,
        sql_aware=False,
    )
    assert "negative-constraints" in prompts.skills_for(chat)
    assert "ground-on-page" in prompts.skills_for(chat)
    course = prompts.PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="theory",
        step_title="theory",
        compact=False,
        sql_aware=False,
    )
    skills = prompts.skills_for(course)
    assert "negative-constraints" in skills
    assert "diagram-craft" in skills


def test_hints_compact_uses_compact_few_shot() -> None:
    prompts = load_service_module("app.domain.prompts")
    compact = prompts.PromptRequest(
        mode="hints",
        phase=None,
        step_kind="code",
        step_title="H",
        compact=True,
        sql_aware=False,
    )
    full = prompts.PromptRequest(
        mode="hints",
        phase=None,
        step_kind="code",
        step_title="H",
        compact=False,
        sql_aware=False,
    )
    assert "few-shot-hints-compact" in prompts.skills_for(compact)
    assert "few-shot-hints" in prompts.skills_for(full)
    assert "few-shot-hints-compact" not in prompts.skills_for(full)


def test_step_looks_like_sql() -> None:
    from studio_contracts.session_schemas import StepContent

    prompts = load_service_module("app.domain.prompts")
    step = StepContent(
        topic_id="t1",
        phase="practice",
        step_id="s1",
        kind="code",
        title="Select",
        content={"instructions": "Write SELECT name FROM cadets"},
        editor={"runtime": "sql", "template": "SELECT 1;"},
    )
    assert prompts.step_looks_like_sql(step)
