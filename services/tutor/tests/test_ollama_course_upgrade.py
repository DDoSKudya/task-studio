from __future__ import annotations

import pytest
from tutor_helpers.loaders import load_service_module


def test_model_for_task_respects_routing_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    monkeypatch.delenv("OLLAMA_TASK_ROUTING", raising=False)
    policy = runtime.load_ollama_runtime_policy(fallback_model="fallback")
    assert runtime.model_for_task(policy, "chat") == policy.model_chat
    policy_off = runtime.OllamaRuntimePolicy(
        accelerator="auto",
        profile="cpu-balanced",
        fallback_model="fallback",
        model_chat="chat-model",
        model_course="course-model",
        model_polish="polish-model",
        model_embed="embed-model",
        request_retries=2,
        max_parallel=1,
        num_ctx_compact=2048,
        num_ctx_full=4096,
        read_timeout_seconds=600.0,
        task_routing_enabled=False,
    )
    assert runtime.model_for_task(policy_off, "polish") == "fallback"


def test_resolve_profile_gpu_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    monkeypatch.setenv("OLLAMA_GPU_AVAILABLE", "1")
    assert runtime.resolve_profile(accelerator="auto", explicit=None) == "gpu-balanced"


def test_resolve_profile_cpu_light_on_low_ram(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    monkeypatch.delenv("OLLAMA_GPU_AVAILABLE", raising=False)
    monkeypatch.setenv("OLLAMA_SYSTEM_RAM_GB", "8")
    assert runtime.resolve_profile(accelerator="auto", explicit=None) == "cpu-light"


def test_stage_task_kind_uses_one_course_model() -> None:
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    for stage in ("analyze", "theory", "quizzes", "code", "polish"):
        assert runtime.stage_task_kind(stage) == "course_topic_bundle"


def test_num_ctx_for_task_compact_lane() -> None:
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    policy = runtime.OllamaRuntimePolicy(
        accelerator="auto",
        profile="cpu-balanced",
        fallback_model="fallback",
        model_chat="chat-model",
        model_course="course-model",
        model_polish="polish-model",
        model_embed="embed-model",
        request_retries=2,
        max_parallel=1,
        num_ctx_compact=2048,
        num_ctx_full=4096,
        read_timeout_seconds=600.0,
        task_routing_enabled=True,
    )
    assert runtime.num_ctx_for_task(policy, task="grade") == 2048
    assert runtime.num_ctx_for_task(policy, task="hints") == 2048
    assert runtime.num_ctx_for_task(policy, task="course_topic_bundle") == 4096
    assert runtime.num_ctx_for_task(policy, task="chat") == 4096
    assert runtime.model_for_task(policy, "grade") == "chat-model"
    assert runtime.model_for_task(policy, "course_topic_bundle") == "course-model"


def test_resolve_llm_target_wires_task_on_ollama() -> None:
    target_mod = load_service_module("app.domain.llm.target")
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    policy = runtime.OllamaRuntimePolicy(
        accelerator="auto",
        profile="cpu-balanced",
        fallback_model="fallback",
        model_chat="chat-model",
        model_course="course-model",
        model_polish="polish-model",
        model_embed="embed-model",
        request_retries=1,
        max_parallel=1,
        num_ctx_compact=2048,
        num_ctx_full=4096,
        read_timeout_seconds=600.0,
        task_routing_enabled=True,
    )
    from types import SimpleNamespace

    config = SimpleNamespace(
        secrets_master_key=None,
        ollama_runtime=policy,
        ollama_model="fallback",
        ollama_url="http://ollama:11434",
        default_provider_url="",
    )
    grade = target_mod.resolve_llm_target(
        config,
        provider_url=None,
        api_key_encrypted=None,
        model=None,
        task="grade",
    )
    course = target_mod.resolve_llm_target(
        config,
        provider_url=None,
        api_key_encrypted=None,
        model=None,
        task="course_topic_bundle",
    )
    assert grade is not None and course is not None
    assert grade.model == "chat-model"
    assert grade.num_ctx == 2048
    assert course.model == "course-model"
    assert course.num_ctx == 4096


def test_pipeline_hooks_resolve_forwards_task() -> None:
    """Регрессия: сборка падала на unexpected keyword argument 'task'."""
    hooks = load_service_module("app.domain.course_from_article.pipeline_hooks")
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    from types import SimpleNamespace

    policy = runtime.OllamaRuntimePolicy(
        accelerator="auto",
        profile="cpu-balanced",
        fallback_model="fallback",
        model_chat="chat-model",
        model_course="course-model",
        model_polish="polish-model",
        model_embed="embed-model",
        request_retries=1,
        max_parallel=1,
        num_ctx_compact=2048,
        num_ctx_full=4096,
        read_timeout_seconds=600.0,
        task_routing_enabled=True,
    )
    config = SimpleNamespace(
        secrets_master_key=None,
        ollama_runtime=policy,
        ollama_model="fallback",
        ollama_url="http://ollama:11434",
        default_provider_url="",
    )
    target = hooks._resolve_llm_target(
        config,
        provider_url=None,
        api_key_encrypted=None,
        model=None,
        task="course_topic_bundle",
    )
    assert target is not None
    assert target.model == "course-model"


def test_resolve_profile_gpu_light_on_low_vram(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    monkeypatch.setenv("OLLAMA_GPU_AVAILABLE", "1")
    monkeypatch.setenv("OLLAMA_GPU_VRAM_GB", "8")
    assert runtime.resolve_profile(accelerator="auto", explicit=None) == "gpu-light"


def test_load_runtime_policy_uses_profile_parallel_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    monkeypatch.setenv("OLLAMA_PROFILE", "gpu-light")
    monkeypatch.delenv("OLLAMA_MAX_PARALLEL", raising=False)
    policy = runtime.load_ollama_runtime_policy(fallback_model="fallback")
    assert policy.max_parallel == 2


def test_is_transient_llm_error() -> None:
    retry = load_service_module("app.domain.llm.retry")
    import httpx

    assert retry.is_transient_llm_error(httpx.ReadTimeout("slow"))
    response = httpx.Response(
        503,
        request=httpx.Request("POST", "http://x/v1/chat/completions"),
    )
    with pytest.raises(Exception) as exc_info:
        response.raise_for_status()
    assert retry.is_transient_llm_error(exc_info.value)


def test_code_suitability_gate_threshold() -> None:
    gate = load_service_module("app.domain.course_from_article.code_suitability")
    score = gate.code_suitability_score(profile="language_learning", runtime="python")
    assert score < 0.45
    assert gate.should_prompt_code_gate(score=score, include_code=True, policy="ask")
    assert not gate.should_prompt_code_gate(score=score, include_code=True, policy="auto_open")


def test_interleaved_manifest_topics() -> None:
    assemble = load_service_module("app.domain.course_from_article.assemble_manifest")
    chapters = [
        {"id": "intro", "title": "Intro"},
        {"id": "advanced", "title": "Advanced"},
    ]
    theory = [
        {
            "id": "theory-intro",
            "kind": "theory",
            "title": "Intro",
            "content": "a",
            "chapter_id": "intro",
        },
        {
            "id": "theory-adv",
            "kind": "theory",
            "title": "Advanced",
            "content": "b",
            "chapter_id": "advanced",
        },
        {
            "id": "theory-intro-2",
            "kind": "theory",
            "title": "Intro cont",
            "content": "a2",
            "chapter_id": "intro",
        },
    ]
    quizzes = [
        {
            "id": "quiz-1",
            "kind": "quiz",
            "title": "Q1",
            "question": "?",
            "choices": ["a"],
            "answer": 0,
            "chapter_id": "intro",
        },
        {
            "id": "quiz-2",
            "kind": "quiz",
            "title": "Q2",
            "question": "?",
            "choices": ["a"],
            "answer": 0,
            "chapter_id": "advanced",
        },
    ]
    codes = [
        {
            "id": "code-1",
            "kind": "code",
            "title": "C1",
            "content": "x",
            "runtime": "python",
            "tests": [],
            "chapter_id": "advanced",
        },
    ]
    manifest = assemble._assemble_interleaved_manifest(
        pack_id="demo",
        title="Demo",
        locale="ru",
        runtime="python",
        runtime_version="3.12",
        chapters=chapters,
        theory_steps=theory,
        quiz_steps=quizzes,
        code_steps=codes,
    )
    topics = manifest["topics"]
    assert isinstance(topics, list)
    assert len(topics) == 2
    assert topics[0]["phases"]["study"]["steps"] == ["theory-intro", "theory-intro-2"]
    assert topics[0]["phases"]["assess"]["steps"] == ["quiz-1"]
    assert topics[1]["phases"]["practice"]["steps"] == ["code-1"]
    assert "chapter_id" not in manifest["steps"]["theory-intro"]
    assert manifest["policies"]["phase_order"] == ["study", "assess", "practice"]


@pytest.mark.asyncio
async def test_probe_ollama_falls_back_when_preferred_missing() -> None:
    from unittest.mock import AsyncMock, MagicMock

    status = load_service_module("app.domain.status")
    config = load_service_module("app.config").load_config()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"models": [{"name": "llama3.2:latest"}]}
    client = AsyncMock()
    client.get.return_value = response

    # Preferred env model is usually qwen; only llama is installed.
    result = await status.probe_ollama(
        client,
        MagicMock(
            ollama_url=config.ollama_url or "http://ollama:11434",
            ollama_model="qwen2.5:3b",
            ollama_runtime=config.ollama_runtime,
        ),
    )
    assert result.ok is True
    assert result.default_model == "llama3.2:latest"
    assert "preferred model" in (result.detail or "").casefold() or "qwen2.5:3b" in (
        result.detail or ""
    )
