from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from tutor_helpers.loaders import load_service_module


@pytest.mark.asyncio
async def test_ollama_content_stage_uses_local_course_runner(monkeypatch) -> None:
    body_mod = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_body")
    target_mod = load_service_module("app.domain.llm.target")

    called: list[str] = []

    seen_seeds: list[int] = []

    async def fake_local(*_args, **kwargs):
        called.append("local")
        seen_seeds.append(len(kwargs.get("exercise_seeds") or []))
        return
        yield  # pragma: no cover

    monkeypatch.setattr(body_mod, "iter_local_course_content", fake_local)

    runtime = SimpleNamespace(profile="gpu-light")
    monkeypatch.setattr(body_mod, "_ollama_runtime_for_config", lambda _cfg: runtime)

    harness = SimpleNamespace(
        provider="ollama",
        run_polish=False,
        compact=True,
        split_long_theory=False,
    )
    buckets = body_mod.ContentBuckets()
    target = target_mod.LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b")
    bands = SimpleNamespace(
        theory=(0.2, 0.4),
        quizzes=(0.4, 0.6),
        code=(0.6, 0.8),
        polish=(0.8, 0.9),
    )
    body = SimpleNamespace(
        include_theory=True,
        include_quizzes=True,
        include_code=False,
        split_long_theory=False,
    )

    async for _ in body_mod.iter_bundle_or_phased_content(
        AsyncMock(),
        target,
        MagicMock(),
        harness=harness,
        body=body,
        chapters=[{"id": "c1", "title": "T", "objective": "o", "source_excerpt": "s"}],
        outcomes=["learn"],
        book_spine={"spine": "x"},
        domain="python",
        use_code=False,
        use_open=False,
        open_practice=False,
        bands=bands,
        warnings=[],
        store=MagicMock(),
        user_id=uuid4(),
        build_id=uuid4(),
        exercise_seeds=[SimpleNamespace(kind="quiz", title="Check routers")],
        buckets=buckets,
        article="article text",
    ):
        pass

    assert called == ["local"]
    assert seen_seeds == [1]


@pytest.mark.asyncio
async def test_external_provider_skips_local_course(monkeypatch) -> None:
    body_mod = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_body")
    target_mod = load_service_module("app.domain.llm.target")

    local_calls: list[str] = []

    async def fake_local(*_args, **_kwargs):
        local_calls.append("local")
        return
        yield  # pragma: no cover

    monkeypatch.setattr(body_mod, "iter_local_course_content", fake_local)

    async def boom_bundles(*_args, **_kwargs):
        raise RuntimeError("phased-path-hit")
        yield  # pragma: no cover

    monkeypatch.setattr(body_mod, "iter_topic_bundle_stages", boom_bundles)

    harness = SimpleNamespace(provider="cursor", run_polish=False, compact=False)
    body = MagicMock()
    body.uses_topic_bundles.return_value = True
    with pytest.raises(RuntimeError, match="phased-path-hit"):
        async for _ in body_mod.iter_bundle_or_phased_content(
            AsyncMock(),
            target_mod.LlmTarget("https://api.example/v1", "k", "gpt"),
            MagicMock(course_topic_bundles=True),
            harness=harness,
            body=body,
            chapters=[],
            outcomes=[],
            book_spine={},
            domain="python",
            use_code=False,
            use_open=False,
            open_practice=False,
            bands=SimpleNamespace(
                theory=(0.2, 0.4),
                quizzes=(0.4, 0.6),
                code=(0.6, 0.8),
                polish=(0.8, 0.9),
            ),
            warnings=[],
            store=MagicMock(),
            user_id=uuid4(),
            build_id=uuid4(),
            exercise_seeds=[],
            buckets=body_mod.ContentBuckets(),
            article="",
        ):
            pass

    assert local_calls == []


@pytest.mark.asyncio
async def test_ollama_honors_no_practice_gate(monkeypatch) -> None:
    schemas = load_service_module("studio_contracts.api.studio_schemas")
    body_mod = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_body")
    from app.domain.llm.target import LlmTarget

    seen: list[bool] = []

    async def fake_local(*_args, **kwargs):
        seen.append(bool(kwargs["body"].include_code))
        return
        yield  # pragma: no cover

    monkeypatch.setattr(body_mod, "iter_local_course_content", fake_local)
    monkeypatch.setattr(
        body_mod,
        "_ollama_runtime_for_config",
        lambda _cfg: SimpleNamespace(profile="gpu-light"),
    )

    body = schemas.CourseFromArticleRequest(
        article="x" * 80,
        include_theory=True,
        include_quizzes=True,
        include_code=True,
        code_suitability_action="no_practice",
    )
    bands = SimpleNamespace(
        theory=(0.2, 0.4),
        quizzes=(0.4, 0.6),
        code=(0.6, 0.8),
        polish=(0.8, 0.9),
    )
    async for _ in body_mod.iter_bundle_or_phased_content(
        AsyncMock(),
        LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
        MagicMock(),
        harness=SimpleNamespace(
            provider="ollama",
            run_polish=False,
            compact=True,
            split_long_theory=False,
        ),
        body=body,
        chapters=[{"id": "c1", "title": "T", "objective": "o", "source_excerpt": "s"}],
        outcomes=["learn"],
        book_spine={"spine": "x"},
        domain="python",
        use_code=False,
        use_open=False,
        open_practice=False,
        bands=bands,
        warnings=[],
        store=MagicMock(),
        user_id=uuid4(),
        build_id=uuid4(),
        exercise_seeds=[],
        buckets=body_mod.ContentBuckets(),
        article="article text",
    ):
        pass

    assert seen == [False]


@pytest.mark.asyncio
async def test_ollama_open_tasks_are_not_code_editor_steps(monkeypatch) -> None:
    schemas = load_service_module("studio_contracts.api.studio_schemas")
    body_mod = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_body")
    from app.domain.llm.target import LlmTarget

    async def fake_local(*_args, **kwargs):
        kwargs["result"].code_steps.append(
            {
                "id": "code-1",
                "kind": "code",
                "title": "Write a Dockerfile",
                "content": "Given: nginx image. Expected: working Dockerfile.",
                "template": "FROM nginx\n",
                "level": "easy",
                "chapter_id": "c1",
            }
        )
        return
        yield  # pragma: no cover

    monkeypatch.setattr(body_mod, "iter_local_course_content", fake_local)
    monkeypatch.setattr(
        body_mod,
        "_ollama_runtime_for_config",
        lambda _cfg: SimpleNamespace(profile="gpu-light"),
    )

    buckets = body_mod.ContentBuckets()
    body = schemas.CourseFromArticleRequest(
        article="x" * 80,
        include_theory=True,
        include_quizzes=False,
        include_code=True,
        code_suitability_action="open_tasks",
    )
    async for _ in body_mod.iter_bundle_or_phased_content(
        AsyncMock(),
        LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
        MagicMock(),
        harness=SimpleNamespace(
            provider="ollama",
            run_polish=False,
            compact=True,
            split_long_theory=False,
        ),
        body=body,
        chapters=[{"id": "c1", "title": "Docker", "objective": "run", "source_excerpt": "s"}],
        outcomes=["run"],
        book_spine={"spine": "x"},
        domain="devops",
        use_code=False,
        use_open=True,
        open_practice=True,
        bands=SimpleNamespace(
            theory=(0.2, 0.4),
            quizzes=(0.4, 0.6),
            code=(0.6, 0.8),
            polish=(0.8, 0.9),
        ),
        warnings=[],
        store=MagicMock(),
        user_id=uuid4(),
        build_id=uuid4(),
        exercise_seeds=[],
        buckets=buckets,
        article="docker compose article",
    ):
        pass

    assert len(buckets.codes) == 1
    assert buckets.codes[0]["kind"] == "task"
    assert buckets.codes[0]["chapter_id"] == "c1"
    assert "Dockerfile" in str(buckets.codes[0]["content"])


@pytest.mark.asyncio
async def test_cloud_topic_bundles_honor_no_practice_gate(monkeypatch) -> None:
    schemas = load_service_module("studio_contracts.api.studio_schemas")
    body_mod = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_body")
    from app.domain.llm.target import LlmTarget

    seen: list[bool] = []

    async def fake_bundles(*_args, **kwargs):
        seen.append(bool(kwargs["body"].include_code))
        return
        yield  # pragma: no cover

    monkeypatch.setattr(body_mod, "iter_topic_bundle_stages", fake_bundles)
    body = schemas.CourseFromArticleRequest(
        article="x" * 80,
        layout="by_topic",
        include_theory=True,
        include_quizzes=True,
        include_code=True,
        code_suitability_action="no_practice",
    )
    async for _ in body_mod.iter_bundle_or_phased_content(
        AsyncMock(),
        LlmTarget("https://api.openai.com/v1", "sk", "gpt-4o"),
        MagicMock(),
        harness=SimpleNamespace(provider="external", run_polish=False, compact=False),
        body=body,
        chapters=[{"id": "c1", "title": "T", "objective": "o", "source_excerpt": "s"}],
        outcomes=["learn"],
        book_spine={"spine": "x"},
        domain="python",
        use_code=False,
        use_open=False,
        open_practice=False,
        bands=SimpleNamespace(
            theory=(0.2, 0.4),
            quizzes=(0.4, 0.6),
            code=(0.6, 0.8),
            polish=(0.8, 0.9),
        ),
        warnings=[],
        store=MagicMock(),
        user_id=uuid4(),
        build_id=uuid4(),
        exercise_seeds=[],
        buckets=body_mod.ContentBuckets(),
        article="article text",
    ):
        pass

    assert seen == [False]


@pytest.mark.asyncio
async def test_bootstrap_unreachable_ollama_is_503(monkeypatch) -> None:
    schemas = load_service_module("studio_contracts.api.studio_schemas")
    body_mod = load_service_module("app.domain.course_from_article.workflow.pipeline.pipeline_body")
    import app.domain.ollama.ensure_models as ensure
    from app.domain.errors import TutorError
    from fastapi import status as http_status

    async def boom_tags(*_args, **_kwargs):
        raise httpx.ConnectError(
            "down",
            request=httpx.Request("GET", "http://ollama:11434/api/tags"),
        )

    monkeypatch.setattr(ensure, "list_ollama_models", boom_tags)
    monkeypatch.setattr(
        body_mod,
        "_fetch_user_settings",
        AsyncMock(
            return_value=SimpleNamespace(provider_url="", api_key_encrypted=None, model=None)
        ),
    )
    config = SimpleNamespace(
        ollama_url="http://ollama:11434",
        ollama_model="qwen2.5:7b",
        ollama_runtime=SimpleNamespace(
            profile="gpu-light",
            read_timeout_seconds=30.0,
            request_retries=1,
        ),
        secrets_master_key=None,
    )
    with pytest.raises(TutorError) as exc:
        await body_mod.bootstrap_course_pipeline(
            AsyncMock(),
            config,
            user_id=uuid4(),
            body=schemas.CourseFromArticleRequest(article="x" * 80),
            active_model=[],
        )
    assert exc.value.status_code == http_status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Ollama is not reachable" in str(exc.value.detail)


def test_local_course_generation_does_not_swap_role_adapters() -> None:
    import inspect

    theory = load_service_module("app.domain.course_from_article.local_course.content.theory")
    loop = load_service_module("app.domain.course_from_article.local_course.content.topic_loop")
    compiler = load_service_module(
        "app.domain.course_from_article.local_course.curriculum.compiler"
    )
    assert "apply_role_adapter" not in inspect.getsource(theory.expand_local_theory_chapter)
    assert "apply_role_adapter" not in inspect.getsource(loop.generate_topic_quizzes)
    assert "apply_role_adapter" not in inspect.getsource(loop.generate_topic_practice)
    assert "apply_role_adapter" not in inspect.getsource(compiler.order_seeds_with_llm)
    messages = load_service_module("app.domain.course_from_article.local_course.content.messages")
    source = inspect.getsource(messages)
    assert "course_from_article_system_prompt" in source
    assert "course_from_article_theory_prose_prompt" in source
