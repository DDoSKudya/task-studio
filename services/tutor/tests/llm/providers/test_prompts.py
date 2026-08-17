from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_system_prompt_replaces_placeholders() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    prompt = prompts.system_prompt_for_phase("study", step_kind="code", step_title="Sum")
    assert "code" in prompt
    assert "Sum" in prompt


def test_system_prompt_for_study_phase() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    prompt = prompts.system_prompt_for_phase("study", step_kind="theory", step_title="Hello")
    assert "study" in prompt.lower()
    assert "Hello" in prompt
    assert "Task Studio" in prompt
    assert "theory" in prompt.lower()
    assert "socratic" in prompt.lower()


def test_system_prompt_for_practice_phase() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    prompt = prompts.system_prompt_for_phase("practice", step_kind="code", step_title="Sum")
    assert "practice" in prompt.lower()
    assert "Sum" in prompt
    assert "attempt" in prompt.lower() or "check" in prompt.lower()
    assert "verify" in prompt.lower()


def test_ollama_profile_adds_token_budget_and_quality() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
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
    prompts = load_service_module("app.domain.prompt_compose.facade")
    prompt = prompts.system_prompt_for_phase(
        "study",
        step_kind="theory",
        step_title="Intro",
        compact=False,
    )
    assert "external" in prompt.lower() or "strong api" in prompt.lower()
    assert "token budget" not in prompt.lower()


def test_hints_system_prompt_includes_kind_overlay() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    prompt = prompts.hints_system_prompt(step_kind="quiz", step_title="Basics")
    assert "Basics" in prompt
    assert "quiz" in prompt.lower()
    assert "2 or 3" in prompt or "2-3" in prompt


def test_pack_studio_system_prompt_requires_json() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    prompt = prompts.pack_studio_system_prompt()
    assert "JSON" in prompt
    assert "manifest" in prompt.lower()
    assert "socratic" not in prompt.lower()


def test_skills_for_matrix() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
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
    prompts = load_service_module("app.domain.prompt_compose.facade")
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
    prompts = load_service_module("app.domain.prompt_compose.facade")
    text = prompts.format_learner_turn("Почему нужен JOIN?")
    assert "<learner_message>" in text
    assert "</learner_message>" in text
    assert "<response_contract>" in text
    assert "JOIN" in text


def test_negative_constraints_in_chat_and_course() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
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


def test_cloud_and_cursor_course_prompts_use_same_ensemble() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    request = load_service_module("app.domain.llm.transport.request")
    target = load_service_module("app.domain.llm.target")
    cursor = target.LlmTarget("http://cursor-proxy:8015/v1", "key", "auto")
    cloud = target.LlmTarget("https://api.openai.com/v1", "sk-test", "gpt-4o")
    ollama = target.LlmTarget("http://ollama:11434/v1", "", "qwen2.5:7b")
    assert not request.looks_like_ollama_endpoint(cursor)
    assert not request.looks_like_ollama_endpoint(cloud)
    assert request.looks_like_ollama_endpoint(ollama)
    for stage in ("analyze", "theory", "quizzes", "code", "tasks", "polish", "quality"):
        prompt = prompts.course_from_article_system_prompt(
            stage=stage,
            compact=False,
            course_profile="programming",
            local_runtime=request.looks_like_ollama_endpoint(cursor),
        )
        folded = prompt.casefold()
        assert "curriculum architect" in folded
        assert "instructional design" in folded
        assert "worked snippet" in folded or "name each api" in folded
        assert "richer explanations" in folded
        assert "small local model" not in folded
    theory = prompts.course_from_article_theory_prose_prompt(
        compact=False,
        course_profile="humanities",
        local_runtime=False,
    )
    assert "curriculum architect" in theory.casefold()
    assert "narrative" in theory.casefold() or "counter-reading" in theory.casefold()
    assert "interpretive throughline" in theory.casefold()
    assert "small local model" not in theory.casefold()
    analyze = prompts.course_from_article_system_prompt(
        stage="analyze",
        compact=False,
        course_profile="humanities",
        local_runtime=False,
    )
    assert "do not force a programming syllabus" in analyze.casefold()
    assert "epitome" in analyze.casefold()
    assert "glossary" in analyze.casefold()
    assert "quality invariants" in analyze.casefold()
    assert "given" in analyze.casefold() and "new" in analyze.casefold()


def test_course_provider_parts_keep_cloud_and_ollama_separate() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    cloud = prompts.PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="theory",
        step_title="theory",
        compact=False,
        sql_aware=False,
    )
    local = prompts.PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="theory",
        step_title="theory",
        compact=True,
        sql_aware=False,
    )
    ollama_full = prompts.PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="polish",
        step_title="polish",
        compact=False,
        sql_aware=False,
        local_runtime=True,
    )
    assert prompts.provider_parts(cloud) == ["provider/external"]
    assert prompts.provider_parts(local) == ["provider/ollama-quality"]
    assert prompts.provider_parts(ollama_full) == ["provider/ollama-quality"]
    ollama_polish = prompts.course_from_article_system_prompt(
        stage="polish", compact=False, local_runtime=True
    )
    cloud_polish = prompts.course_from_article_system_prompt(
        stage="polish", compact=False, local_runtime=False
    )
    assert "small local model" in ollama_polish.lower()
    assert "small local model" not in cloud_polish.lower()


def test_course_prompt_layers_stable_prefix_then_stage() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    prompt = prompts.course_from_article_system_prompt(
        stage="quizzes",
        compact=False,
        course_profile="programming",
        local_runtime=False,
    )
    role_at = prompt.casefold().find("curriculum architect")
    parts_at = prompt.find("Author settings for THIS run")
    always_at = prompt.find("Each pipeline stage returns one JSON object only")
    provider_at = prompt.find("richer explanations")
    domain_at = prompt.find("Domain overlay: programming")
    stage_at = prompt.find("Skill: quiz assessment design")
    assert min(role_at, parts_at, always_at, provider_at, domain_at, stage_at) >= 0
    assert role_at < parts_at < always_at < provider_at < domain_at < stage_at


def test_course_compact_skips_chat_token_budget() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    course = prompts.PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="analyze",
        step_title="analyze",
        compact=True,
        sql_aware=False,
    )
    skills = prompts.skills_for(course)
    assert "curriculum-synthesis" in skills
    assert "token-budget" not in skills


def test_hints_compact_uses_compact_few_shot() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
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


def test_course_parts_off_skip_assess_skills() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    from app.domain.course_from_article.common.runtime.course_context import set_course_parts

    set_course_parts(theory=True, quizzes=False, practice=False)
    try:
        quiz_prompt = prompts.course_from_article_system_prompt(
            stage="quizzes",
            compact=False,
            course_profile="humanities",
            local_runtime=False,
        )
        theory = prompts.course_from_article_theory_prose_prompt(
            compact=False,
            course_profile="humanities",
            local_runtime=False,
        )
        analyze = prompts.course_from_article_system_prompt(
            stage="analyze",
            compact=False,
            course_profile="humanities",
            local_runtime=False,
        )
        folded = quiz_prompt.casefold()
        assert "quizzes: off" in folded
        assert "practice: off" in folded
        assert "skill: quiz assessment design" not in folded
        assert "do not invent a missing part" in folded
        assert "complete book" in theory.casefold()
        assert "syllabus is an argument" in theory.casefold()
        assert "quiz-testable" not in analyze.casefold()
        quiz_req = prompts.PromptRequest(
            mode="course_from_article",
            phase=None,
            step_kind="quizzes",
            step_title="quizzes",
            compact=False,
            sql_aware=False,
            course_profile="humanities",
        )
        code_req = prompts.PromptRequest(
            mode="course_from_article",
            phase=None,
            step_kind="code",
            step_title="code",
            compact=False,
            sql_aware=False,
            course_profile="programming",
        )
        assert "quiz-assessment-design" not in prompts.skills_for(quiz_req)
        code_skills = prompts.skills_for(code_req)
        assert "practice-as-drill" not in code_skills
        assert "code-task-ladder" not in code_skills
    finally:
        set_course_parts(theory=True, quizzes=True, practice=True)


def test_course_parts_on_keep_assess_and_domain_shape() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    from app.domain.course_from_article.common.runtime.course_context import set_course_parts

    set_course_parts(theory=True, quizzes=True, practice=True)
    prompt = prompts.course_from_article_system_prompt(
        stage="quizzes",
        compact=False,
        course_profile="programming",
        local_runtime=False,
    )
    folded = prompt.casefold()
    assert "quizzes: on" in folded
    assert "practice: on" in folded
    assert "skill: quiz assessment design" in folded
    assert "tiny working slice" in folded


def test_theory_prompt_asks_for_book_flow_not_frames() -> None:
    prompts = load_service_module("app.domain.prompt_compose.facade")
    theory = prompts.course_from_article_theory_prose_prompt(
        compact=False,
        course_profile="programming",
        local_runtime=False,
    )
    folded = theory.casefold()
    assert "calm running prose" in folded
    assert "blockquote callouts" in folded
    assert "assertion" in folded
    assert "worked snippet" in folded or "name each api" in folded
    polish = prompts.course_from_article_system_prompt(
        stage="polish",
        compact=False,
        course_profile="programming",
        local_runtime=False,
    )
    assert "fold boxed asides" in polish.casefold()


def test_step_looks_like_sql() -> None:
    from studio_contracts.api.session_schemas import StepContent

    prompts = load_service_module("app.domain.prompt_compose.facade")
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
