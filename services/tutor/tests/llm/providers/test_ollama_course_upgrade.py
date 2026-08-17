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

    hooks = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_hooks")
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
    assert policy.max_parallel == 1
    assert policy.model_course == "qwen2.5:7b"


def test_is_transient_llm_error() -> None:
    retry = load_service_module("app.domain.llm.transport.retry")
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
    gate = load_service_module("app.domain.course_from_article.practice.code_suitability")
    score = gate.code_suitability_score(profile="language_learning", runtime="python")
    assert score < 0.45
    assert gate.should_prompt_code_gate(score=score, include_code=True, policy="ask")
    assert not gate.should_prompt_code_gate(score=score, include_code=True, policy="auto_open")


def test_interleaved_manifest_topics() -> None:
    assemble = load_service_module("app.domain.course_from_article.pack.assemble_manifest")
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


def test_interleaved_manifest_no_cross_topic_clone_on_slug_collision() -> None:

    assemble = load_service_module("app.domain.course_from_article.pack.assemble_manifest")
    base = "razdelenie-modelej-i-ustranenie-ciklicheskih-importov"
    assert base[:40] == f"{base}-2"[:40]
    chapters = [
        {"id": base, "title": "Разделение моделей"},
        {"id": f"{base}-2", "title": "Разделение моделей (2)"},
        {"id": f"{base}-3", "title": "Разделение моделей (3)"},
    ]

    theory = [
        {
            "id": f"theory-{index}",
            "kind": "theory",
            "title": f"T{index}",
            "content": "x",
        }
        for index in range(1, 4)
    ]
    quizzes = [
        {
            "id": f"quiz-{index}",
            "kind": "quiz",
            "title": "Same harvest title",
            "question": f"Q{index}?",
            "choices": ["a"],
            "answer": 0,
        }
        for index in range(1, 4)
    ]
    codes = [
        {
            "id": f"code-{index}",
            "kind": "code",
            "title": "Practice",
            "content": "x",
            "runtime": "python",
            "tests": [],
        }
        for index in range(1, 4)
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
    assert len(topics) == 3
    assert len({topic["id"] for topic in topics}) == 3
    study_lens = [len(topic["phases"]["study"]["steps"]) for topic in topics]
    assess_lens = [len(topic["phases"]["assess"]["steps"]) for topic in topics]
    practice_lens = [len(topic["phases"]["practice"]["steps"]) for topic in topics]
    assert study_lens == [1, 1, 1]
    assert assess_lens == [1, 1, 1]
    assert practice_lens == [1, 1, 1]
    assert sum(study_lens) + sum(assess_lens) + sum(practice_lens) == 9


def test_interleaved_manifest_respects_topic_bundle_unique_keys() -> None:

    assemble = load_service_module("app.domain.course_from_article.pack.assemble_manifest")
    base = "struktuirovanie-koda-i-arkhitektura-prilozheniya"
    assert len(base) >= 40
    assert base[:40] == f"{base}-2"[:40] == f"{base}-3"[:40]
    chapters = [
        {"id": base, "title": "Структурирование кода и архитектура приложения"},
        {"id": f"{base}-2", "title": "Структурирование кода и архитектура приложения (2)"},
        {"id": f"{base}-3", "title": "Структурирование кода и архитектура приложения (3)"},
        {"id": "razdelenie-modelej", "title": "Разделение моделей"},
    ]
    topic_keys = assemble._topic_keys(chapters)
    assert len(set(topic_keys)) == 4

    theory = [
        {
            "id": f"theory-{index}",
            "kind": "theory",
            "title": chapters[index]["title"],
            "content": "x",
            "chapter_id": topic_keys[index],
        }
        for index in range(4)
    ]
    quizzes = [
        {
            "id": f"quiz-{index}",
            "kind": "quiz",
            "title": chapters[index]["title"],
            "question": f"Q{index}?",
            "choices": ["a", "b", "c", "d"],
            "answer": 0,
            "chapter_id": topic_keys[index],
        }
        for index in range(4)
    ]
    codes = [
        {
            "id": f"code-{index}",
            "kind": "code",
            "title": f"Practice {index}",
            "content": "x",
            "runtime": "python",
            "tests": [],
            "chapter_id": topic_keys[index],
        }
        for index in range(4)
    ]

    broken_theory = [{**step, "chapter_id": base[:40]} for step in theory]
    broken = assemble._assemble_interleaved_manifest(
        pack_id="demo",
        title="Demo",
        locale="ru",
        runtime="python",
        runtime_version="3.12",
        chapters=chapters,
        theory_steps=broken_theory,
        quiz_steps=[{**step, "chapter_id": base[:40]} for step in quizzes],
        code_steps=[{**step, "chapter_id": base[:40]} for step in codes],
    )
    broken_study = [len(t["phases"]["study"]["steps"]) for t in broken["topics"]]
    assert broken_study[0] >= 3
    assert broken_study[1] == 0 or broken_study[2] == 0

    fixed = assemble._assemble_interleaved_manifest(
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
    study_lens = [len(t["phases"]["study"]["steps"]) for t in fixed["topics"]]
    assess_lens = [len(t["phases"]["assess"]["steps"]) for t in fixed["topics"]]
    practice_lens = [len(t["phases"]["practice"]["steps"]) for t in fixed["topics"]]
    assert study_lens == [1, 1, 1, 1]
    assert assess_lens == [1, 1, 1, 1]
    assert practice_lens == [1, 1, 1, 1]
    assert len({t["id"] for t in fixed["topics"]}) == 4


def test_duplicate_raw_chapter_ids_keep_first_module_not_last() -> None:

    assemble = load_service_module("app.domain.course_from_article.pack.assemble_manifest")
    short = "Основы композиции модулей в учебном проекте"
    long = "Основы композиции модулей с практическими примерами из статьи"
    chapters = [
        {"id": "topic", "title": short},
        {"id": "topic", "title": long},
        {"id": "topic", "title": short},
        {"id": "topic", "title": long},
        {"id": "topic", "title": short},
        {"id": "topic", "title": long},
        {"id": "closing", "title": "Сводка и следующие шаги"},
    ]
    keys = assemble._topic_keys(chapters)
    assert keys[0] == "topic"
    assert keys[5] == "topic-6"
    theory = [
        {
            "id": f"t{index}",
            "kind": "theory",
            "title": chapters[index]["title"],
            "content": "x" * 80,
            "chapter_id": "topic",
        }
        for index in range(6)
    ] + [
        {
            "id": "t6",
            "kind": "theory",
            "title": chapters[6]["title"],
            "content": "y" * 80,
            "chapter_id": keys[6],
        }
    ]
    manifest = assemble._assemble_interleaved_manifest(
        pack_id="demo",
        title="Demo",
        locale="ru",
        runtime="python",
        runtime_version="3.12",
        chapters=chapters,
        theory_steps=theory,
        quiz_steps=[],
        code_steps=[],
    )
    study = [len(topic["phases"]["study"]["steps"]) for topic in manifest["topics"]]
    assert study[0] == 6
    assert study[5] == 0
    assert study[6] == 1
    keyed = [
        {
            "id": f"t{index}",
            "kind": "theory",
            "title": chapters[index]["title"],
            "content": "x" * 80,
            "chapter_id": keys[index],
        }
        for index in range(7)
    ]
    fixed = assemble._assemble_interleaved_manifest(
        pack_id="demo",
        title="Demo",
        locale="ru",
        runtime="python",
        runtime_version="3.12",
        chapters=chapters,
        theory_steps=keyed,
        quiz_steps=[],
        code_steps=[],
    )
    assert [len(t["phases"]["study"]["steps"]) for t in fixed["topics"]] == [1, 1, 1, 1, 1, 1, 1]


def test_enrich_keeps_stable_chapter_id(monkeypatch) -> None:
    analyze = load_service_module(
        "app.domain.course_from_article.workflow.pipeline.pipeline_analyze"
    )
    schemas = load_service_module("studio_contracts.api.studio_schemas")

    async def fake_stage_json(*_args, **_kwargs):
        return {
            "chapter": {
                "id": "colliding-slug",
                "title": "Other title",
                "source_excerpt": "excerpt " * 40,
                "purpose": "learn",
                "learning_objective": "obj",
            }
        }

    monkeypatch.setattr(analyze, "_stage_json", fake_stage_json)
    body = schemas.CourseFromArticleRequest(
        article="x" * 100,
        title="t",
        locale="ru",
        include_theory=True,
        include_quizzes=False,
        include_code=False,
    )
    chapter = {
        "id": "stable-unique-id",
        "title": "Original",
        "source_excerpt": "seed " * 40,
    }

    async def _run():
        return await analyze._enrich_one_chapter(
            client=None,
            target=object(),
            body=body,
            compact=True,
            article="a" * 100,
            sources=[],
            chapter=chapter,
            index=0,
            total=1,
            outcomes=[],
        )

    import asyncio

    enriched = asyncio.run(_run())
    assert enriched["id"] == "stable-unique-id"


def test_ensure_distinct_titles_suffixes_clones() -> None:
    bundles = load_service_module("app.domain.course_from_article.workflow.stages.topic_bundles")
    steps = [
        {"id": "q1", "title": "Same", "question": "A?"},
        {"id": "q2", "title": "Same", "question": "B?"},
        {"id": "q3", "title": "Same", "question": "C?"},
    ]
    bundles._ensure_distinct_titles(steps)
    assert steps[0]["title"] == "Same"
    assert steps[1]["title"] == "Same (2)"
    assert steps[2]["title"] == "Same (3)"


def test_interleaved_manifest_uniquifies_colliding_step_ids() -> None:
    assemble = load_service_module("app.domain.course_from_article.pack.assemble_manifest")
    manifest = assemble._assemble_interleaved_manifest(
        pack_id="demo",
        title="Demo",
        locale="ru",
        runtime="python",
        runtime_version="3.12",
        chapters=[
            {"id": "a", "title": "A"},
            {"id": "b", "title": "B"},
        ],
        theory_steps=[
            {"id": "theory-1", "kind": "theory", "title": "T", "content": "x", "chapter_id": "a"},
            {"id": "theory-1", "kind": "theory", "title": "T2", "content": "y", "chapter_id": "b"},
        ],
        quiz_steps=[
            {
                "id": "quiz-1",
                "kind": "quiz",
                "title": "Q",
                "question": "one?",
                "choices": ["a", "b", "c", "d"],
                "answer": 0,
                "chapter_id": "a",
            },
            {
                "id": "quiz-1",
                "kind": "quiz",
                "title": "Q2",
                "question": "two?",
                "choices": ["a", "b", "c", "d"],
                "answer": 1,
                "chapter_id": "b",
            },
        ],
        code_steps=[],
    )
    assert len(manifest["steps"]) == 4
    assess_a = manifest["topics"][0]["phases"]["assess"]["steps"]
    assess_b = manifest["topics"][1]["phases"]["assess"]["steps"]
    assert assess_a != assess_b
    assert manifest["steps"][assess_a[0]]["answer"] == 0
    assert manifest["steps"][assess_b[0]]["answer"] == 1


def test_phased_manifest_uniquifies_colliding_quiz_ids() -> None:
    assemble = load_service_module("app.domain.course_from_article.pack.assemble_manifest")
    manifest = assemble._assemble_manifest(
        pack_id="demo",
        title="Demo",
        locale="ru",
        runtime="python",
        runtime_version="3.12",
        theory_steps=[
            {"id": "theory-1", "kind": "theory", "title": "T", "content": "x"},
        ],
        quiz_steps=[
            {
                "id": "quiz-1",
                "kind": "quiz",
                "title": "Q",
                "question": "one?",
                "choices": ["a", "b", "c", "d"],
                "answer": 0,
            },
            {
                "id": "quiz-1",
                "kind": "quiz",
                "title": "Q2",
                "question": "two?",
                "choices": ["a", "b", "c", "d"],
                "answer": 1,
            },
        ],
        code_steps=[],
    )
    assess = manifest["topics"][0]["phases"]["assess"]["steps"]
    assert assess == ["quiz-1", "quiz-1-2"]
    assert manifest["steps"]["quiz-1"]["answer"] == 0
    assert manifest["steps"]["quiz-1-2"]["answer"] == 1


@pytest.mark.asyncio
async def test_probe_ollama_falls_back_when_preferred_missing() -> None:
    from unittest.mock import AsyncMock, MagicMock

    status = load_service_module("app.domain.model_runtime.status")
    config = load_service_module("app.config").load_config()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"models": [{"name": "qwen2.5:3b"}]}
    client = AsyncMock()
    client.get.return_value = response

    result = await status.probe_ollama(
        client,
        MagicMock(
            ollama_url=config.ollama_url or "http://ollama:11434",
            ollama_model="qwen2.5:7b",
            ollama_runtime=config.ollama_runtime,
        ),
    )

    assert result.ok is True
    assert result.active_course_model == "qwen2.5:3b"


def test_resolve_task_model_returns_none_when_nothing_installed() -> None:
    select = load_service_module("app.domain.ollama.model_select")
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    policy = runtime.OllamaRuntimePolicy(
        accelerator="gpu",
        profile="gpu-light",
        fallback_model="qwen2.5:7b",
        model_chat="qwen2.5:3b",
        model_course="qwen2.5:7b",
        model_polish="qwen2.5:7b",
        model_embed="nomic-embed-text",
        request_retries=1,
        max_parallel=1,
        num_ctx_compact=4096,
        num_ctx_full=8192,
        read_timeout_seconds=600.0,
        task_routing_enabled=True,
    )
    model, is_fallback = select.resolve_task_model(
        policy, "course_topic_bundle", installed=["nomic-embed-text"]
    )
    assert model is None
    assert is_fallback is True
    model2, fallback2 = select.resolve_task_model(
        policy, "course_topic_bundle", installed=["qwen2.5:3b"]
    )
    assert model2 == "qwen2.5:3b"
    assert fallback2 is True


def test_resolve_task_model_prefers_7b_over_3b_for_course() -> None:
    select = load_service_module("app.domain.ollama.model_select")
    runtime = load_service_module("app.domain.ollama.runtime_policy")
    policy = runtime.OllamaRuntimePolicy(
        accelerator="gpu",
        profile="gpu-balanced",
        fallback_model="qwen2.5:7b",
        model_chat="qwen2.5:7b",
        model_course="missing-course-model",
        model_polish="qwen2.5:7b",
        model_embed="nomic-embed-text",
        request_retries=1,
        max_parallel=1,
        num_ctx_compact=4096,
        num_ctx_full=8192,
        read_timeout_seconds=600.0,
        task_routing_enabled=True,
    )
    model, is_fallback = select.resolve_task_model(
        policy,
        "course_topic_bundle",
        installed=["qwen2.5:3b", "qwen2.5:7b"],
    )
    assert model == "qwen2.5:7b"
    assert is_fallback is True
