from __future__ import annotations

import inspect
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from tutor_helpers.loaders import load_service_module


def test_quiz_from_seed_requires_real_choices() -> None:
    quizzes = load_service_module("app.domain.course_from_article.practice.quiz_generate")
    harvest = load_service_module("app.domain.course_from_article.practice.source_exercise_harvest")
    bare = harvest.HarvestedExercise(kind="quiz", title="Check", body="Explain routers.")
    assert quizzes._quiz_from_seed(bare, 0) is None
    with_choices = harvest.HarvestedExercise(
        kind="quiz",
        title="Check routers",
        body=(
            "Which layout keeps imports acyclic?\n"
            "- Split routers with APIRouter by package\n"
            "- Keep every route inside main.py forever\n"
            "- Disable dependency injection entirely\n"
            "- Ignore lifespan hooks for startup work\n"
        ),
    )
    quiz = quizzes._quiz_from_seed(with_choices, 0)
    assert quiz is not None
    assert len(quiz["choices"]) == 4


def test_sectional_continues_capped_at_one() -> None:
    expand = load_service_module("app.domain.course_from_article.curriculum.theory.theory_expand")
    source = inspect.getsource(expand._expand_theory_sectional)
    assert "min(1, max(0, max_continues))" in source


def test_no_practice_turns_off_code_on_local_body() -> None:
    body_mod = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_body")
    schemas = load_service_module("studio_contracts.api.studio_schemas")
    body = schemas.CourseFromArticleRequest(
        article="x" * 80,
        include_code=True,
        code_suitability_action="no_practice",
    )
    use_code, use_open = body_mod.practice_flags(
        body=body, open_practice=False, action="no_practice"
    )
    gated = body_mod.body_after_practice_gate(body, use_code=use_code, use_open=use_open)
    assert gated.include_code is False
    assert use_open is False


def test_open_tasks_keep_practice_but_rewrite_kind() -> None:
    body_mod = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_body")
    schemas = load_service_module("studio_contracts.api.studio_schemas")
    body = schemas.CourseFromArticleRequest(article="x" * 80, include_code=True)
    use_code, use_open = body_mod.practice_flags(body=body, open_practice=True, action="open_tasks")
    gated = body_mod.body_after_practice_gate(body, use_code=use_code, use_open=use_open)
    assert gated.include_code is True
    converted = body_mod.codes_for_practice_mode(
        [
            {
                "id": "code-easy",
                "kind": "code",
                "title": "Run nginx",
                "content": "Given a compose file. Expected a running container.",
                "template": "FROM nginx\n",
                "level": "easy",
                "runtime": "bash",
            }
        ],
        use_open=use_open,
        default_runtime="bash",
    )
    assert converted[0]["kind"] == "task"
    assert converted[0]["runtime"] == "bash"


def test_course_bootstrap_does_not_warm_chat_models() -> None:
    body_mod = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_body")
    source = inspect.getsource(body_mod.bootstrap_course_pipeline)
    model_source = inspect.getsource(body_mod._ensure_course_model)
    assert "ensure_profile_models" not in source
    assert "pull_ollama_model" in model_source
    assert "list_ollama_models" in model_source


def test_pipeline_entry_delegates_to_pipeline_body() -> None:
    pipeline = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline")
    body = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_body")
    source = inspect.getsource(pipeline._iter_course_from_article_body)
    assert "iter_course_pipeline_body" in source
    assert inspect.isasyncgenfunction(body.iter_course_pipeline_body)


def test_course_harness_policy_ollama_cpu_vs_gpu() -> None:
    policy_mod = load_service_module(
        "app.domain.course_from_article.common.runtime.provider_policy"
    )
    target_mod = load_service_module("app.domain.llm.target")
    runtime = load_service_module("app.domain.ollama.runtime_policy")

    cpu_policy = runtime.OllamaRuntimePolicy(
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
    gpu_policy = replace(cpu_policy, profile="gpu-balanced")
    config = SimpleNamespace(
        ollama_url="http://ollama:11434",
        default_provider_url="",
    )
    cpu_target = target_mod.LlmTarget(
        base_url="http://ollama:11434/v1",
        model="qwen2.5:3b",
        api_key=None,
        num_ctx=4096,
    )
    gpu_target = replace(cpu_target, model="qwen2.5:7b")

    cpu = policy_mod.course_harness_policy(config, cpu_target, ollama_profile=cpu_policy.profile)
    gpu = policy_mod.course_harness_policy(config, gpu_target, ollama_profile=gpu_policy.profile)
    assert cpu.provider == "ollama"
    assert gpu.provider == "ollama"
    assert cpu.compact is False
    assert gpu.compact is False
    assert cpu.run_polish is True
    assert cpu.strategy_pack == "author-full"
    assert cpu.quiz_fail_soft is False
    assert cpu.code_fail_soft is False
    assert cpu.split_long_theory is True
    assert cpu.quiz_max_tokens == 2000
    assert cpu.max_quiz_attempts == 5
    assert cpu.theory_max_continues == gpu.theory_max_continues == 1
    assert cpu.sectional_theory is gpu.sectional_theory is True
    assert cpu.theory_sentences_per_window == 1
    assert gpu.theory_sentences_per_window == 3
    assert cpu.theory_quality_rounds == 2
    assert cpu.quiz_quality_rounds == 2
    assert cpu.practice_quality_rounds == 2


def test_local_and_cloud_share_course_llm_limits() -> None:
    limits_mod = load_service_module("app.domain.course_from_article.common.runtime.llm_limits")
    policy_mod = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    harness_mod = load_service_module(
        "app.domain.course_from_article.common.runtime.provider_policy"
    )
    target_mod = load_service_module("app.domain.llm.target")
    volume = limits_mod.COURSE_LLM
    local = policy_mod.local_course_policy_for(profile="gpu-light", model="qwen2.5:7b")
    config = SimpleNamespace(ollama_url="http://ollama:11434", default_provider_url="")
    ollama = harness_mod.course_harness_policy(
        config,
        target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
        ollama_profile="gpu-light",
    )
    cloud = harness_mod.course_harness_policy(
        config,
        target_mod.LlmTarget("https://api.openai.com/v1", "sk", "gpt-4o"),
        ollama_profile="gpu-light",
    )
    assert local.quiz_max_tokens == ollama.quiz_max_tokens == volume.quiz_max_tokens
    assert cloud.quiz_max_tokens == volume.quiz_max_tokens
    assert local.theory_max_continues == volume.theory_max_continues
    assert ollama.theory_max_continues == 1
    assert local.strategy_pack == ollama.strategy_pack == "author-full"
    assert local.run_polish is True
    assert ollama.run_polish is True
    assert local.quality_rounds == ollama.theory_quality_rounds == volume.quality_rounds
    assert cloud.strategy_pack == "author-full"
    assert cloud.run_polish is True
    assert cloud.theory_quality_rounds == volume.quality_rounds
    assert ollama.max_quiz_attempts == cloud.max_quiz_attempts == volume.max_quiz_attempts
    assert limits_mod.json_stage_temperature(local_runtime=True) == volume.json_temperature
    assert limits_mod.json_stage_temperature(local_runtime=False) == volume.json_temperature_cloud


def test_cursor_sdk_is_not_routed_to_ollama() -> None:
    policy_mod = load_service_module(
        "app.domain.course_from_article.common.runtime.provider_policy"
    )
    from app.domain.llm.target import LlmTarget

    config = SimpleNamespace(ollama_url="http://ollama:11434")
    cursor = LlmTarget("http://cursor-proxy:8015/v1", "key", "auto")
    assert policy_mod.detect_course_provider(config, cursor) == "cursor"
    harness = policy_mod.course_harness_policy(config, cursor, ollama_profile="gpu-light")
    assert harness.provider == "cursor"
    assert harness.theory_quality_rounds == 2
    assert harness.split_long_theory is True


def test_cloud_provider_is_not_routed_to_ollama() -> None:
    policy_mod = load_service_module(
        "app.domain.course_from_article.common.runtime.provider_policy"
    )
    from app.domain.llm.target import LlmTarget

    config = SimpleNamespace(ollama_url="http://ollama:11434")
    cloud = LlmTarget("https://api.openai.com/v1", "sk", "gpt-4o")
    assert policy_mod.detect_course_provider(config, cloud) == "external"
    harness = policy_mod.course_harness_policy(config, cloud, ollama_profile="gpu-light")
    assert harness.provider == "external"
    assert harness.quiz_quality_rounds == 2


def test_course_harness_policy_external_strict_quizzes() -> None:
    policy_mod = load_service_module(
        "app.domain.course_from_article.common.runtime.provider_policy"
    )
    target_mod = load_service_module("app.domain.llm.target")
    config = SimpleNamespace(ollama_url="", default_provider_url="https://api.example.com")
    external = target_mod.LlmTarget(
        base_url="https://api.example.com",
        model="gpt-4o-mini",
        api_key="secret",
        num_ctx=None,
    )
    harness = policy_mod.course_harness_policy(config, external, ollama_profile="cpu-balanced")
    assert harness.provider == "external"
    assert harness.compact is False
    assert harness.quiz_fail_soft is False
    assert harness.code_fail_soft is False
    assert harness.split_long_theory is True
    assert harness.sectional_theory is False
    assert harness.theory_quality_rounds == 2
    assert harness.quiz_quality_rounds == 2
    assert harness.practice_quality_rounds == 2


def _usable_quiz(*, quiz_id: str = "q1") -> dict[str, object]:
    return {
        "id": quiz_id,
        "question": "Which statement best matches the FastAPI routing guidance in the article?",
        "choices": [
            "Split routers with APIRouter by package",
            "Keep every route inside main.py forever",
            "Disable dependency injection entirely",
            "Ignore lifespan hooks for startup work",
        ],
        "answer": 0,
    }


def test_topic_bundle_complete_gates() -> None:
    bundles = load_service_module("app.domain.course_from_article.workflow.stages.topic_bundles")
    schemas = load_service_module("studio_contracts.api.studio_schemas")
    body = schemas.CourseFromArticleRequest(
        article="x" * 80,
        locale="ru",
        include_theory=True,
        include_quizzes=True,
        include_code=True,
    )
    quiz = _usable_quiz()
    complete = bundles.topic_bundle_complete(
        body,
        theory_steps=[{"id": "t1", "content": "x" * 420}],
        quizzes=[quiz],
        codes=[{"id": "c1"}],
    )
    incomplete = bundles.topic_bundle_complete(
        body,
        theory_steps=[{"id": "t1", "content": "x" * 420}],
        quizzes=[],
        codes=[{"id": "c1"}],
    )
    assert complete is True
    assert incomplete is False
    soft_sticky = bundles.topic_bundle_complete(
        body,
        theory_steps=[{"id": "t1", "content": "x" * 420}],
        quizzes=[],
        codes=[{"id": "c1"}],
        quiz_fail_soft=True,
    )
    assert soft_sticky is False
    zero_quota = bundles.topic_bundle_complete(
        body,
        theory_steps=[{"id": "t1", "content": "x" * 420}],
        quizzes=[],
        codes=[],
        expect_quizzes=False,
        expect_codes=False,
    )
    assert zero_quota is True
    empty_theory = bundles.topic_bundle_complete(
        body,
        theory_steps=[{"id": "t1", "content": ""}],
        quizzes=[quiz],
        codes=[{"id": "c1"}],
    )
    assert empty_theory is False
    thin_theory = bundles.topic_bundle_complete(
        body,
        theory_steps=[{"id": "t1", "content": "x" * 300}],
        quizzes=[quiz],
        codes=[{"id": "c1"}],
    )
    assert thin_theory is False
    placeholder_quiz = bundles.topic_bundle_complete(
        body,
        theory_steps=[{"id": "t1", "content": "x" * 420}],
        quizzes=[
            {
                "id": "q-bad",
                "question": "What?",
                "choices": [
                    "Matches the article",
                    "Opposite of the article",
                    "Unrelated detail",
                    "Too vague to verify",
                ],
                "answer": 0,
            }
        ],
        codes=[{"id": "c1"}],
    )
    assert placeholder_quiz is False


def test_per_topic_counts_use_per_topic_values() -> None:
    bundles = load_service_module("app.domain.course_from_article.workflow.stages.topic_bundles")
    schemas = load_service_module("studio_contracts.api.studio_schemas")
    body = schemas.CourseFromArticleRequest(
        article="x" * 80,
        locale="ru",
        quiz_count=6,
        code_count=3,
        practice_count=3,
        include_quizzes=True,
        include_code=True,
    )
    counts = [
        bundles._per_topic_counts(body, topic_total=5, topic_index=index) for index in range(5)
    ]
    assert all(item == (6, 3) for item in counts)


def test_per_topic_counts_zero_when_module_off() -> None:
    bundles = load_service_module("app.domain.course_from_article.workflow.stages.topic_bundles")
    schemas = load_service_module("studio_contracts.api.studio_schemas")
    body = schemas.CourseFromArticleRequest(
        article="x" * 80,
        locale="ru",
        quiz_count=2,
        practice_count=2,
        include_quizzes=False,
        include_code=True,
    )
    quizzes, practice = bundles._per_topic_counts(body, topic_total=8, topic_index=0)
    assert quizzes == 0
    assert practice == 2


@pytest.mark.asyncio
async def test_probe_ollama_reports_resolved_course_model() -> None:
    status_mod = load_service_module("app.domain.model_runtime.status")
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
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"models": [{"name": "qwen2.5:7b"}, {"name": "qwen2.5:3b"}]}
    client = AsyncMock()
    client.get.return_value = response

    result = await status_mod.probe_ollama(
        client,
        SimpleNamespace(
            ollama_url="http://ollama:11434",
            ollama_model="qwen2.5:7b",
            ollama_runtime=policy,
        ),
    )
    assert result.ok is True
    assert result.active_course_model == "qwen2.5:7b"


@pytest.mark.asyncio
async def test_probe_ollama_missing_model_does_not_fake_selection() -> None:
    status_mod = load_service_module("app.domain.model_runtime.status")
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
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"models": [{"name": "nomic-embed-text"}]}
    client = AsyncMock()
    client.get.return_value = response

    result = await status_mod.probe_ollama(
        client,
        SimpleNamespace(
            ollama_url="http://ollama:11434",
            ollama_model="qwen2.5:7b",
            ollama_runtime=policy,
        ),
    )
    assert result.ok is False
    assert not (result.active_course_model or "").strip()


@pytest.mark.asyncio
async def test_topic_bundle_resume_regenerates_incomplete_quizzes(tmp_path) -> None:
    bundles_mod = load_service_module(
        "app.domain.course_from_article.workflow.stages.topic_bundles"
    )
    schemas = load_service_module("studio_contracts.api.studio_schemas")
    store_mod = load_service_module("app.domain.course_build.store")

    body = schemas.CourseFromArticleRequest(
        article="x" * 80,
        locale="ru",
        layout="by_topic",
        include_theory=False,
        include_quizzes=True,
        include_code=False,
        quiz_count=2,
        build_id=__import__("uuid").uuid4(),
    )
    harness_mod = load_service_module(
        "app.domain.course_from_article.common.runtime.provider_policy"
    )
    harness = harness_mod.CourseHarnessPolicy(
        provider="ollama",
        compact=True,
        run_polish=False,
        quiz_fail_soft=False,
        code_fail_soft=False,
        max_quiz_attempts=2,
        quiz_max_tokens=800,
        split_long_theory=False,
        theory_max_continues=2,
        sectional_theory=False,
        theory_quality_rounds=0,
        quiz_quality_rounds=0,
        practice_quality_rounds=0,
    )
    store = store_mod.CourseBuildStore(tmp_path, ttl_days=1)
    user_id = __import__("uuid").uuid4()
    meta = store.create(
        user_id=user_id,
        request_payload=body.model_dump(mode="json"),
        title="Resume test",
        mode="topic_bundles",
    )
    build_id = __import__("uuid").UUID(meta.build_id)
    store.save_topic(
        user_id,
        build_id,
        "intro",
        theories=[],
        quizzes=[],
        codes=[],
    )

    client = AsyncMock()
    target = object()
    chapters = [{"id": "intro", "title": "Intro"}]
    result = bundles_mod.TopicBundleResult()
    events: list[dict[str, object]] = []

    async def _collect() -> None:
        async for event in bundles_mod.iter_topic_bundle_stages(
            client,
            target,
            body=body,
            harness=harness,
            chapters=chapters,
            outcomes=[],
            book_spine={},
            domain="general",
            use_code=False,
            use_open=False,
            band=(0.2, 0.8),
            warnings=[],
            result=result,
            store=store,
            user_id=user_id,
            build_id=build_id,
        ):
            events.append(event)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            bundles_mod,
            "generate_quizzes",
            AsyncMock(return_value=[{"id": "q1", "kind": "quiz", "title": "Q"}]),
        )
        await _collect()

    assert any(event.get("message_key") == "topicBundleRunning" for event in events)
    assert len(result.quiz_steps) == 1
