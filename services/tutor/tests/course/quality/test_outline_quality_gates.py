from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.domain.course_from_article.curriculum.outline.normalize_outline import _normalize_chapters
from app.domain.course_from_article.workflow.pipeline.pipeline_analyze import _fullness_warning
from studio_contracts.api.studio_schemas import CourseFromArticleRequest
from tutor_helpers.loaders import load_service_module


def test_harness_always_runs_full_quality_path() -> None:

    policy = load_service_module("app.domain.course_from_article.common.runtime.provider_policy")
    target_mod = load_service_module("app.domain.llm.target")
    config = SimpleNamespace(ollama_url="http://ollama:11434", default_provider_url="")
    ollama = target_mod.LlmTarget("http://ollama:11434/v1", "x", "qwen2.5:7b", num_ctx=8192)
    external = target_mod.LlmTarget("https://api.example.com/v1", "key", "strong-model")
    for target, profile in (
        (ollama, "cpu-light"),
        (ollama, "gpu-light"),
        (external, "cpu-balanced"),
    ):
        harness = policy.course_harness_policy(config, target, ollama_profile=profile)
        assert harness.compact is False
        assert harness.strategy_pack == "author-full"
        assert harness.run_polish is True


def test_normalize_chapters_dedupes_duplicate_titles_and_ids() -> None:
    chapters = _normalize_chapters(
        [
            {
                "id": "stack",
                "title": "The MLOps Stack",
                "source_excerpt": "Same excerpt body about MLOps platforms and tools. " * 20,
            },
            {
                "id": "stack",
                "title": "The MLOps Stack",
                "source_excerpt": "Same excerpt body about MLOps platforms and tools. " * 20,
            },
            {
                "id": "other",
                "title": "The MLOps Stack",
                "source_excerpt": "Same excerpt body about MLOps platforms and tools. " * 20,
            },
        ]
    )
    assert [item["title"] for item in chapters] == ["The MLOps Stack"]
    assert [item["id"] for item in chapters] == ["stack"]


def test_normalize_chapters_near_duplicate_titles() -> None:
    chapters = _normalize_chapters(
        [
            {
                "id": "a",
                "title": "The MLOps Stack Overview",
                "source_excerpt": (
                    "Feature stores and model registries keep training reproducible. " * 30
                ),
            },
            {
                "id": "b",
                "title": "MLOps: The Stack Overview",
                "source_excerpt": (
                    "Kubernetes serving and canary rollouts for online inference. " * 30
                ),
            },
            {
                "id": "c",
                "title": "Deploying models to production",
                "source_excerpt": "Blue-green deploys and rollback playbooks. " * 30,
            },
        ]
    )

    assert len(chapters) == 3
    assert chapters[0]["title"] == "The MLOps Stack Overview"
    assert "Stack Overview" in chapters[1]["title"] or "(2)" in chapters[1]["title"]
    assert chapters[2]["title"] == "Deploying models to production"


def test_normalize_chapters_drops_true_clones_only() -> None:
    shared = "Feature stores and model registries keep training reproducible. " * 40
    chapters = _normalize_chapters(
        [
            {"id": "a", "title": "Структура проекта", "source_excerpt": shared},
            {"id": "b", "title": "Структура проекта MLOps", "source_excerpt": shared},
        ]
    )
    assert len(chapters) == 1


def test_fullness_warning_does_not_treat_short_toc_as_a_defect() -> None:
    assert _fullness_warning(got=5, wanted=8) == (
        "sources supported 5 of 8 requested theory slides"
    )


@pytest.mark.asyncio
async def test_analyze_keeps_source_backed_chapter_count() -> None:
    analyze = load_service_module(
        "app.domain.course_from_article.workflow.pipeline.pipeline_analyze"
    )
    corpus = "x" * 30_000
    body = CourseFromArticleRequest(article=corpus, theory_count=8, locale="en")
    seed_payload = {
        "chapters": [
            {
                "id": f"c{i}",
                "title": f"Chapter {i}",
                "source_excerpt": f"Teachable excerpt for chapter {i}. " * 20,
            }
            for i in range(5)
        ],
        "outcomes": ["Use the API"],
        "domain": "code",
        "title": "API course",
        "pack_id": "api-course",
    }
    result = analyze.AnalyzeStageResult()
    with patch.object(
        analyze,
        "_stage_json",
        new_callable=AsyncMock,
        return_value=seed_payload,
    ) as stage_json:
        events = [
            event
            async for event in analyze.iter_analyze_stage(
                AsyncMock(),
                object(),
                body=body,
                compact=False,
                article=corpus,
                sources=[{"title": "Doc", "content": corpus}],
                band_analyze=(0.0, 0.2),
                result=result,
            )
        ]
    assert events
    assert len(result.chapters) == 5
    assert result.warning == "sources supported 5 of 8 requested theory slides"
    assert stage_json.await_count >= 1
