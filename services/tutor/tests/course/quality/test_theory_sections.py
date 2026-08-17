from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from studio_contracts.api.studio_schemas import CourseFromArticleRequest
from tutor_helpers.loaders import load_service_module


def test_split_theory_excerpt_caps_section_count() -> None:
    sections_mod = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    )
    chunks = [
        f"## Topic {index}\n" + ("Substantial teaching paragraph about the topic. " * 20)
        for index in range(12)
    ]
    parts = sections_mod.split_theory_excerpt("\n\n".join(chunks), target_chars=400)
    assert len(parts) <= sections_mod._MAX_SECTION_PARTS
    assert "Topic 0" in parts[0]
    assert "Topic 11" in "\n".join(parts)


def test_split_theory_excerpt_merges_tiny_heading_chunks() -> None:
    sections_mod = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    )
    excerpt = "\n\n".join(
        [
            "## A\nShort note one about routing.",
            "## B\nShort note two about models.",
            "## C\nShort note three about lifespan.",
            "## D\nShort note four about deps.",
        ]
    )
    parts = sections_mod.split_theory_excerpt(excerpt, target_chars=1100)
    assert len(parts) < 4
    joined = "\n".join(parts)
    assert "Short note one" in joined
    assert "Short note four" in joined


def test_split_theory_excerpt_by_headings() -> None:
    sections_mod = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    )
    excerpt = (
        "## Intro\n"
        "First idea about FastAPI routing and request models.\n\n"
        "## Depth\n"
        "Second idea about dependency injection and lifespan hooks in apps.\n\n"
        "## Traps\n"
        "Third idea about common mistakes with async endpoints.\n"
    )
    parts = sections_mod.split_theory_excerpt(excerpt)
    joined = "\n".join(parts)
    assert "Intro" in joined
    assert "Depth" in joined
    assert "Traps" in joined
    assert "First idea" in joined
    assert "Third idea" in joined


def test_split_theory_excerpt_packs_paragraphs() -> None:
    sections_mod = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    )
    paragraphs = [
        f"Paragraph {index} with enough teaching substance for packing. " * 8 for index in range(6)
    ]
    excerpt = "\n\n".join(paragraphs)
    parts = sections_mod.split_theory_excerpt(excerpt, target_chars=900)
    assert len(parts) >= 2
    stitched = sections_mod.stitch_theory_sections(parts)
    assert "Paragraph 0" in stitched
    assert "Paragraph 5" in stitched


def test_pack_sentence_windows_overlaps() -> None:
    sections_mod = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    )
    text = (
        "First sentence about routers. Second sentence about models. "
        "Third sentence about lifespan. Fourth sentence about Depends. "
        "Fifth sentence about yield."
    )
    windows = sections_mod.pack_sentence_windows(
        text, sentences_per_window=3, overlap=1, max_windows=24
    )
    assert len(windows) >= 2
    assert "First sentence" in windows[0]
    assert "Fifth sentence" in windows[-1]

    first_tail = windows[0].split(". ")[-1].rstrip(".")
    assert first_tail in windows[1]


def test_adaptive_window_grows_when_too_many_sentences() -> None:
    sections_mod = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    )
    size = sections_mod.adaptive_window_size(80, preferred=3, max_windows=10)
    assert size >= 8


def test_cpu_strategy_can_use_one_sentence_per_request() -> None:
    sections_mod = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    )
    text = "First fact. Second fact. Third fact."
    windows = sections_mod.pack_sentence_windows(
        text,
        sentences_per_window=1,
        max_windows=10_000,
    )
    assert windows == ["First fact.", "Second fact.", "Third fact."]


def test_align_section_cache_keeps_partial() -> None:
    sections_mod = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    )
    padded = sections_mod.align_section_cache(["first draft"], 3)
    assert padded == ["first draft", "", ""]
    assert sections_mod.align_section_cache(["a", "b", "c", "d"], 3) == []


def test_theory_chapter_digest_skips_headings() -> None:
    sections_mod = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    )
    digest = sections_mod.theory_chapter_digest(
        "# Title\n\nFirst sentence about models. Second sentence about routers."
    )
    assert "Title" not in digest
    assert "models" in digest.casefold()


@pytest.mark.asyncio
async def test_sectional_expand_calls_llm_per_section() -> None:
    theory = load_service_module("app.domain.course_from_article.curriculum.theory.theory_expand")
    body = CourseFromArticleRequest(
        article="x" * 80,
        title="course",
        locale="ru",
    )
    chapter = {
        "id": "c1",
        "title": "FastAPI basics",
        "source_excerpt": (
            "## Routing\n"
            + ("Use APIRouter to group related endpoints and keep modules small. " * 20)
            + "\n\n## Models\n"
            + ("Pydantic models validate payloads before your handler runs. " * 20)
        ),
        "purpose": "teach routing",
        "source_titles": "A",
        "bridge_from_prev": "",
        "assumes_known": "",
        "must_not_reteach": "",
    }
    drafts = [
        "## Routing\n\nГруппируйте эндпоинты через APIRouter.\n",
        "## Models\n\nПроверяйте тела запросов через Pydantic.\n",
    ]
    calls: list[str] = []

    async def fake_complete(*_args, **kwargs):
        calls.append(str(kwargs.get("user_message") or ""))
        return drafts.pop(0)

    async def boom_meta(*_args, **_kwargs):
        raise AssertionError("sectional path with 2+ sections must not fall back to meta")

    async def passthrough_locale(*_args, **kwargs):
        return kwargs["content"]

    target = theory.LlmTarget(
        base_url="http://ollama:11434/v1",
        api_key="x",
        model="qwen2.5:7b",
        num_ctx=4096,
    )
    section_hits: list[tuple[int, int]] = []

    async def on_section(section_index: int, section_count: int) -> None:
        section_hits.append((section_index, section_count))

    with (
        patch.object(theory, "complete_text_until_done", new=AsyncMock(side_effect=fake_complete)),
        patch.object(theory, "_stage_json", new=AsyncMock(side_effect=boom_meta)),
        patch.object(
            theory,
            "_ensure_theory_locale",
            new=AsyncMock(side_effect=passthrough_locale),
        ),
    ):
        step = await theory._expand_one_theory_chapter(
            AsyncMock(),
            target,
            body=body,
            compact=False,
            chapter=chapter,
            chapters=[chapter],
            outcomes=["route"],
            book_spine={},
            index=0,
            sectional=True,
            max_continues=1,
            on_section=on_section,
        )

    assert len(calls) == 2
    assert section_hits == [(1, 2), (2, 2)]
    body_text = str(step.get("content") or "")
    assert "APIRouter" in body_text or "Pydantic" in body_text
    assert "theory_section" in calls[0]
    assert "THIS section" in calls[0] or "source_excerpt" in calls[0]


@pytest.mark.asyncio
async def test_non_sectional_external_still_uses_meta() -> None:
    theory = load_service_module("app.domain.course_from_article.curriculum.theory.theory_expand")
    body = CourseFromArticleRequest(article="x" * 80, title="course", locale="en")
    chapter = {
        "id": "c1",
        "title": "One",
        "source_excerpt": "Short excerpt only.",
        "purpose": "",
        "source_titles": "",
        "bridge_from_prev": "",
        "assumes_known": "",
        "must_not_reteach": "",
    }
    stages: list[str] = []

    async def fake_stage_json(*_args, **_kwargs):
        stages.append("meta")
        return {"id": "c1", "kind": "theory", "title": "One"}

    async def fake_complete(*_args, **_kwargs):
        stages.append("content")
        return "# One\n\nTeach the short excerpt carefully.\n"

    async def passthrough_locale(*_args, **kwargs):
        return kwargs["content"]

    target = theory.LlmTarget(
        base_url="https://api.example.com",
        api_key="x",
        model="gpt",
    )
    with (
        patch.object(theory, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)),
        patch.object(
            theory,
            "complete_text_until_done",
            new=AsyncMock(side_effect=fake_complete),
        ),
        patch.object(
            theory,
            "_ensure_theory_locale",
            new=AsyncMock(side_effect=passthrough_locale),
        ),
    ):
        step = await theory._expand_one_theory_chapter(
            AsyncMock(),
            target,
            body=body,
            compact=False,
            chapter=chapter,
            chapters=[chapter],
            outcomes=["x"],
            book_spine={},
            index=0,
            sectional=False,
        )

    assert stages == ["meta", "content"]
    assert step["kind"] == "theory"


@pytest.mark.asyncio
async def test_sectional_expand_resumes_partial_window_cache() -> None:
    theory = load_service_module("app.domain.course_from_article.curriculum.theory.theory_expand")
    body = CourseFromArticleRequest(article="x" * 80, title="course", locale="ru")
    chapter = {
        "id": "c1",
        "title": "FastAPI basics",
        "source_excerpt": (
            "One sentence about routers. Two sentence about models. "
            "Three sentence about lifespan. Four sentence about Depends. "
            "Five sentence about yield. Six sentence about middleware."
        ),
        "purpose": "teach routing",
        "source_titles": "A",
        "bridge_from_prev": "",
        "assumes_known": "",
        "must_not_reteach": "",
    }
    calls: list[str] = []
    saved: list[tuple[int, int, str]] = []

    async def fake_complete(*_args, **kwargs):
        calls.append(str(kwargs.get("user_message") or ""))
        return f"Generated window {len(calls)} about FastAPI routing.\n"

    target = theory.LlmTarget(
        base_url="http://ollama:11434/v1",
        api_key="x",
        model="qwen2.5:7b",
        num_ctx=4096,
    )
    with patch.object(theory, "complete_text_until_done", new=AsyncMock(side_effect=fake_complete)):
        step = await theory._expand_one_theory_chapter(
            AsyncMock(),
            target,
            body=body,
            compact=False,
            chapter=chapter,
            chapters=[chapter],
            outcomes=["x"],
            book_spine={},
            index=0,
            sectional=True,
            sentences_per_window=3,
            load_section_drafts=lambda: ["Cached first window about routing and models."],
            save_section_draft=lambda index, total, content: saved.append((index, total, content)),
        )

    assert len(calls) >= 1
    assert "Cached first window" in str(step.get("content") or "")
    assert "Generated window" in str(step.get("content") or "")
    assert saved


@pytest.mark.asyncio
async def test_sectional_expand_skips_llm_when_windows_cached() -> None:
    theory = load_service_module("app.domain.course_from_article.curriculum.theory.theory_expand")
    body = CourseFromArticleRequest(article="x" * 80, title="course", locale="ru")
    chapter = {
        "id": "c1",
        "title": "FastAPI basics",
        "source_excerpt": (
            "One sentence about routers. Two sentence about models. "
            "Three sentence about lifespan. Four sentence about Depends. "
            "Five sentence about yield. Six sentence about middleware."
        ),
        "purpose": "",
        "source_titles": "",
        "bridge_from_prev": "",
        "assumes_known": "",
        "must_not_reteach": "",
    }
    windows = load_service_module(
        "app.domain.course_from_article.curriculum.theory.theory_sections"
    ).pack_sentence_windows(chapter["source_excerpt"], sentences_per_window=3)
    cached = [f"Draft {index} about FastAPI routing in packages." for index in range(len(windows))]

    async def boom(*_args, **_kwargs):
        raise AssertionError("cached windows must not call the model")

    target = theory.LlmTarget(
        base_url="http://ollama:11434/v1",
        api_key="x",
        model="qwen2.5:7b",
        num_ctx=4096,
    )
    with patch.object(theory, "complete_text_until_done", new=AsyncMock(side_effect=boom)):
        step = await theory._expand_one_theory_chapter(
            AsyncMock(),
            target,
            body=body,
            compact=False,
            chapter=chapter,
            chapters=[chapter],
            outcomes=["x"],
            book_spine={},
            index=0,
            sectional=True,
            sentences_per_window=3,
            load_section_drafts=lambda: cached,
        )

    body_text = str(step.get("content") or "")
    assert "Draft 0" in body_text
    assert "Draft 1" in body_text
