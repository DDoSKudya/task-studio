from __future__ import annotations

import asyncio
import json
import re
from unittest.mock import AsyncMock, patch

import pytest
from studio_contracts.pack import collect_manifest_errors
from studio_contracts.studio_schemas import CourseArticleInput, CourseFromArticleRequest
from tutor_helpers.loaders import load_service_module


def _fake_llm_target():
    import sys

    LlmTarget = sys.modules["app.domain.llm.target"].LlmTarget
    return LlmTarget(base_url="http://ollama:11434/v1", api_key=None, model="qwen2.5:7b")


def _theory_expand_mod():
    import sys

    return sys.modules["app.domain.course_from_article.theory_expand"]


def test_parse_json_object_accepts_fenced_payload() -> None:
    course = load_service_module("app.domain.course_from_article")
    raw = """```json
{"outcomes": ["use Path"], "chapters": [{"id": "intro", "title": "Intro"}]}
```"""
    parsed = course._parse_json_object(raw)
    assert parsed is not None
    assert parsed["outcomes"] == ["use Path"]


def test_articles_from_body_multi_and_legacy() -> None:
    course = load_service_module("app.domain.course_from_article")
    multi = CourseFromArticleRequest(
        articles=[
            CourseArticleInput(title="A", content="x" * 50),
            CourseArticleInput(title="B", content="y" * 50),
        ]
    )
    sources = course._articles_from_body(multi)
    assert len(sources) == 2
    assert sources[0]["title"] == "A"

    solo = CourseFromArticleRequest(article="z" * 90, title="Solo")
    solo_sources = course._articles_from_body(solo)
    assert len(solo_sources) == 1
    assert solo_sources[0]["title"] == "Solo"


def test_normalize_deviations() -> None:
    course = load_service_module("app.domain.course_from_article")
    sources = [{"title": "One", "content": "a"}, {"title": "Two", "content": "b"}]
    rows = course._normalize_deviations(
        [{"summary": "API conflict on Path.cwd", "sources": ["One", "Two"]}],
        sources,
    )
    assert len(rows) == 1
    assert "Path.cwd" in rows[0].summary


def test_assemble_manifest_nested_phases_valid() -> None:
    course = load_service_module("app.domain.course_from_article")
    theory = [
        {
            "id": "theory-intro",
            "kind": "theory",
            "title": "Intro",
            "content": "Path helps with filesystem paths.",
        }
    ]
    quizzes = [
        {
            "id": f"quiz-{i}",
            "kind": "quiz",
            "title": f"Q{i}",
            "question": f"Question {i}?",
            "choices": ["a", "b", "c", "d"],
            "answer": 0,
        }
        for i in range(1, 4)
    ]
    codes = [
        {
            "id": f"code-{level}",
            "kind": "code",
            "title": level,
            "content": f"Do {level}",
            "runtime": "python",
            "runtime_version": "3.12",
            "template": "def solve(x: int) -> int:\n    return x\n",
            "tests": [{"input": [1], "output": 1}],
        }
        for level in ("easy", "medium", "hard")
    ]
    manifest = course._assemble_manifest(
        pack_id="pathlib-course",
        title="Pathlib",
        locale="ru",
        runtime="python",
        runtime_version="3.12",
        theory_steps=theory,
        video_steps=[
            {
                "id": "video-intro",
                "kind": "video",
                "title": "Intro talk",
                "video_url": "https://www.youtube.com/watch?v=abcdefghijk",
            }
        ],
        quiz_steps=quizzes,
        code_steps=codes,
    )
    phases = manifest["topics"][0]["phases"]
    assert phases["study"] == {"steps": ["theory-intro", "video-intro"]}
    assert phases["assess"]["steps"] == ["quiz-1", "quiz-2", "quiz-3"]
    assert phases["practice"]["steps"] == ["code-easy", "code-medium", "code-hard"]
    assert manifest["policies"]["phase_order"] == ["study", "assess", "practice"]
    assert manifest["steps"]["video-intro"]["kind"] == "video"
    assert collect_manifest_errors(manifest) == []
    from studio_contracts.manifest import iter_positions

    positions = iter_positions(manifest)
    assert [p.phase for p in positions[:2]] == ["study", "study"]
    assert positions[-1].phase == "practice"


def test_video_steps_from_sources_dedupes() -> None:
    course = load_service_module("app.domain.course_from_article")
    from studio_contracts.studio_schemas import CourseArticleVideo

    sources = [
        {
            "title": "A",
            "content": "x" * 50,
            "videos": [
                CourseArticleVideo(url="https://www.youtube.com/watch?v=abcdefghijk"),
                CourseArticleVideo(url="https://www.youtube.com/watch?v=abcdefghijk"),
            ],
        }
    ]
    steps = course._video_steps_from_sources(sources)
    assert len(steps) == 1
    assert steps[0]["kind"] == "video"
    assert steps[0]["video_url"].endswith("abcdefghijk")


def test_articles_from_body_picks_markdown_videos() -> None:
    course = load_service_module("app.domain.course_from_article")
    body = CourseFromArticleRequest(
        articles=[
            CourseArticleInput(
                title="With video",
                content=("Watch https://youtu.be/dQw4w9WgXcQ " + ("x" * 40)),
            )
        ]
    )
    sources = course._articles_from_body(body)
    assert len(sources[0]["videos"]) == 1


def test_course_from_article_theory_skills_include_diagram() -> None:
    prompts = load_service_module("app.domain.prompts")
    req = prompts.PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="theory",
        step_title="theory",
        compact=False,
        sql_aware=False,
    )
    skills = prompts.skills_for(req)
    assert "expand-dense-prose" in skills
    assert "diagram-craft" in skills


def test_normalize_book_spine_and_chapter_bridges() -> None:
    course = load_service_module("app.domain.course_from_article")
    spine = course._normalize_book_spine(
        {
            "voice": "calm essayist",
            "address": "ты",
            "throughline": "Session as a desk",
            "glossary": [{"term": "Session", "sense": "desk"}],
            "recurring_metaphors": ["desk / warehouse"],
        }
    )
    assert spine["address"] == "ты"
    assert "Session: desk" in spine["glossary"]
    assert "desk / warehouse" in spine["metaphors"]

    chapters = course._normalize_chapters(
        [
            {
                "id": "ch-1",
                "title": "Foundations",
                "source_excerpt": "excerpt one",
                "bridge_from_prev": "Course opening",
                "assumes_known": [],
                "must_not_reteach": ["nothing yet"],
            },
            {
                "id": "ch-2",
                "title": "Depth",
                "source_excerpt": "excerpt two",
                "bridge_from_prev": "You already have the desk",
                "assumes_known": ["Session metaphor"],
                "must_not_reteach": ["what ORM is"],
            },
        ]
    )
    assert chapters[1]["bridge_from_prev"].startswith("You already")
    assert "Session metaphor" in chapters[1]["assumes_known"]
    assert "what ORM is" in chapters[1]["must_not_reteach"]


def test_chapter_opening_and_apply_book_polish_edits() -> None:
    course = load_service_module("app.domain.course_from_article")
    body = "First paragraph about Path.\n\nSecond paragraph keeps depth.\n\nThird stays."
    opening, cut = course._chapter_opening(body, 40)
    assert "First paragraph" in opening
    assert cut > 0
    assert body[cut:].lstrip().startswith("Second")

    steps = [
        {
            "id": "theory-a",
            "title": "A",
            "content": (
                "Old intro that repeats basics.\n\nBody of chapter A stays with more detail here."
            ),
        },
        {
            "id": "theory-b",
            "title": "B",
            "content": (
                "Another repeated intro about the same basics again.\n\n"
                "Body of chapter B stays with concrete examples and a short recap."
            ),
        },
    ]
    digests = [
        {
            "id": "theory-a",
            "title": "A",
            "opening": "Old intro that repeats basics.",
            "opening_chars": len("Old intro that repeats basics."),
            "content_chars": len(str(steps[0]["content"])),
        },
        {
            "id": "theory-b",
            "title": "B",
            "opening": "Another repeated intro about the same basics again.",
            "opening_chars": len("Another repeated intro about the same basics again."),
            "content_chars": len(str(steps[1]["content"])),
        },
    ]
    revised_b = (
        "You already have the Path map — now open a desk for writes. "
        "Keep the earlier metaphor; this chapter only adds the session."
    )
    applied = course._apply_book_polish_edits(
        steps,
        {
            "edits": [
                {
                    "id": "theory-a",
                    "opening": "Path is a map — keep that picture as you read further.",
                },
                {"id": "theory-b", "content": revised_b},
            ]
        },
        digests,
    )
    assert applied == 2
    assert str(steps[0]["content"]).startswith("Path is a map")
    assert "Body of chapter A stays" in str(steps[0]["content"])
    assert str(steps[1]["content"]).startswith("You already have the Path map")


def test_course_polish_skills() -> None:
    prompts = load_service_module("app.domain.prompts")
    req = prompts.PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="polish",
        step_title="",
        compact=False,
        sql_aware=False,
    )
    skills = prompts.skills_for(req)
    assert "book-polish" in skills
    assert "expand-dense-prose" not in skills


def test_theory_serial_count_keeps_prefix_for_book_voice() -> None:
    course = load_service_module("app.domain.course_from_article")
    assert course._theory_serial_count(1, compact=False) == 1
    assert course._theory_serial_count(2, compact=False) == 2
    assert course._theory_serial_count(8, compact=False) == 2
    assert course._theory_serial_count(8, compact=True) == 8
    assert course._theory_parallel_limit(compact=True) == 1
    assert course._theory_parallel_limit(compact=False) == 3


@pytest.mark.asyncio
async def test_expand_theory_compact_uses_single_content_call() -> None:
    theory = load_service_module("app.domain.course_from_article.theory_expand")
    body = CourseFromArticleRequest(
        article="abc helps define interfaces. " * 20,
        title="abc",
        locale="ru",
    )
    chapter = {
        "id": "c1",
        "title": "Usage of abc",
        "source_excerpt": "Abstract base classes…",
        "purpose": "",
        "source_titles": "",
        "bridge_from_prev": "",
        "assumes_known": "",
        "must_not_reteach": "",
    }
    calls: list[str] = []

    async def fake_complete(*_args, **_kwargs):
        calls.append("content")
        return (
            "# Использование\n\n"
            "Используйте `abc.ABC` для интерфейсов и контрактов в коде приложения.\n"
        )

    async def boom_stage_json(*_args, **_kwargs):
        raise AssertionError("compact theory must not call meta JSON stage")

    target = theory.LlmTarget(
        base_url="http://ollama:11434/v1",
        api_key="x",
        model="llama",
    )
    with (
        patch.object(theory, "complete_text_until_done", new=AsyncMock(side_effect=fake_complete)),
        patch.object(theory, "_stage_json", new=AsyncMock(side_effect=boom_stage_json)),
    ):
        step = await theory._expand_one_theory_chapter(
            AsyncMock(),
            target,
            body=body,
            compact=True,
            chapter=chapter,
            chapters=[chapter],
            outcomes=["use abc"],
            book_spine={},
            index=0,
        )

    assert calls == ["content"]
    assert step["kind"] == "theory"
    assert "abc" in str(step.get("content") or "").casefold() or step["title"]


@pytest.mark.asyncio
async def test_expand_theory_rewrites_wrong_language() -> None:
    theory = load_service_module("app.domain.course_from_article.theory_expand")
    body = CourseFromArticleRequest(
        article="arabic source text " * 20,
        title="course",
        locale="ru",
    )
    chapter = {
        "id": "c1",
        "title": "Idea",
        "source_excerpt": "مصدر عربي",
        "purpose": "",
        "source_titles": "",
        "bridge_from_prev": "",
        "assumes_known": "",
        "must_not_reteach": "",
    }
    drafts = [
        "This chapter explains the idea in English only with enough letters for detection.",
        "Эта глава объясняет идею на русском языке и даёт рабочий пример для ученика.",
    ]

    async def fake_complete(*_args, **_kwargs):
        return drafts.pop(0)

    target = theory.LlmTarget(
        base_url="http://ollama:11434/v1",
        api_key="x",
        model="llama",
    )
    with patch.object(theory, "complete_text_until_done", new=AsyncMock(side_effect=fake_complete)):
        step = await theory._expand_theory_compact(
            AsyncMock(),
            target,
            body=body,
            chapter=chapter,
            chapters=[chapter],
            outcomes=["learn"],
            book_spine={},
            index=0,
        )

    assert (
        "русск" in str(step.get("content") or "").casefold()
        or "глава" in str(step.get("content") or "").casefold()
    )
    assert not drafts


@pytest.mark.asyncio
async def test_course_stream_emits_ping_while_waiting() -> None:
    keep = load_service_module("app.domain.course_from_article.stream_keepalive")

    async def slow_events():
        await asyncio.sleep(0.05)
        yield {
            "type": "stage",
            "stage": "theory",
            "status": "running",
            "progress": 0.2,
            "message": "x",
        }
        yield {"type": "done", "progress": 1.0, "message": "ok"}

    with patch.object(keep, "_COURSE_STREAM_PING_SECONDS", 0.01):
        frames = [frame async for frame in keep.iter_course_sse_with_pings(slow_events())]

    texts = [frame.decode() for frame in frames]
    assert any('"type": "ping"' in text or '"type":"ping"' in text for text in texts)
    assert any("theory" in text for text in texts)


def test_theory_user_message_includes_book_spine() -> None:
    course = load_service_module("app.domain.course_from_article")
    body = CourseFromArticleRequest(article="x" * 90, locale="ru")
    chapters = [
        {
            "id": "a",
            "title": "A",
            "source_excerpt": "ea",
            "purpose": "",
            "source_titles": "",
            "bridge_from_prev": "Open the book",
            "assumes_known": "",
            "must_not_reteach": "",
        },
        {
            "id": "b",
            "title": "B",
            "source_excerpt": "eb",
            "purpose": "",
            "source_titles": "",
            "bridge_from_prev": "Continue the desk",
            "assumes_known": "Session metaphor",
            "must_not_reteach": "what ORM is",
        },
    ]
    msg = course._theory_user_message(
        chapters[1],
        body,
        ["learn"],
        chapters=chapters,
        index=1,
        book_spine={
            "voice": "calm",
            "address": "ты",
            "throughline": "desk",
            "glossary": "Session: desk",
            "metaphors": "desk / warehouse",
        },
    )
    assert "## Book spine" in msg
    assert "throughline: desk" in msg
    assert "Continue the desk" in msg
    assert "Must not reteach" in msg
    assert "one book" in msg.lower()
    assert "Output language (mandatory)" in msg
    assert "Russian" in msg


def test_locale_prompt_ignores_source_language() -> None:
    locale = load_service_module("app.domain.course_from_article.course_locale")
    assert locale.normalize_course_locale("EN-us") == "en"
    assert locale.normalize_course_locale("ru") == "ru"
    block = locale.locale_prompt_block("ru")
    assert "Russian" in block
    assert "ANY language" in block
    assert 'exactly "ru"' in block


def test_course_from_article_skills_include_consistency() -> None:
    prompts = load_service_module("app.domain.prompts")
    req = prompts.PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="consistency",
        step_title="consistency",
        compact=True,
        sql_aware=False,
    )
    skills = prompts.skills_for(req)
    assert "article-consistency" in skills
    assert "course-stage-json" in skills


def test_course_from_article_analyze_skills_include_curriculum() -> None:
    prompts = load_service_module("app.domain.prompts")
    req = prompts.PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="analyze",
        step_title="analyze",
        compact=False,
        sql_aware=False,
    )
    skills = prompts.skills_for(req)
    assert "instructional-design" in skills
    assert "curriculum-synthesis" in skills
    assert "course-stage-json" in skills


def test_course_from_article_theory_skills_include_instructional_design() -> None:
    prompts = load_service_module("app.domain.prompts")
    req = prompts.PromptRequest(
        mode="course_from_article",
        phase=None,
        step_kind="theory",
        step_title="theory",
        compact=False,
        sql_aware=False,
    )
    skills = prompts.skills_for(req)
    assert "instructional-design" in skills
    assert "expand-dense-prose" in skills


def test_combined_corpus_fair_shares_sources() -> None:
    course = load_service_module("app.domain.course_from_article")
    sources = [
        {"title": "Foundations", "content": "INTRO-" + ("A" * 20_000)},
        {"title": "Advanced", "content": "DEPTH-" + ("B" * 20_000)},
    ]
    corpus = course._combined_corpus(sources)
    assert "## Source 1: Foundations" in corpus
    assert "## Source 2: Advanced" in corpus
    assert "INTRO-" in corpus
    assert "DEPTH-" in corpus
    assert len(corpus) <= course._MAX_ARTICLE_FOR_PROMPT


@pytest.mark.asyncio
async def test_consistency_gate_stops_without_ignore(tutor_config) -> None:
    import uuid

    course = load_service_module("app.domain.course_from_article")
    body = CourseFromArticleRequest(
        articles=[
            CourseArticleInput(title="Pathlib", content=("Path is great. " * 8)),
            CourseArticleInput(title="Asyncio", content=("Event loop basics. " * 8)),
        ],
        locale="ru",
        ignore_deviations=False,
    )

    async def fake_stage_json(*_args, stage: str, **_kwargs):
        if stage == "consistency":
            return {
                "related": False,
                "similarity": 0.2,
                "shared_topic": "",
                "deviations": [
                    {
                        "summary": "Different topics: filesystem vs concurrency",
                        "sources": ["Pathlib", "Asyncio"],
                    }
                ],
            }
        raise AssertionError(f"unexpected stage {stage}")

    with (
        patch.object(
            course,
            "fetch_user_settings",
            new=AsyncMock(
                return_value=AsyncMock(
                    provider_url="http://ollama:11434/v1",
                    api_key_encrypted=None,
                    model="qwen2.5:7b",
                )
            ),
        ),
        patch.object(course, "resolve_llm_target", return_value=_fake_llm_target()),
        patch.object(course, "is_ollama_target", return_value=True),
        patch.object(course, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)),
    ):
        events = [
            event
            async for event in course.iter_course_from_article(
                AsyncMock(),
                tutor_config,
                user_id=uuid.uuid4(),
                body=body,
            )
        ]

    assert events[-1]["type"] == "consistency_gate"
    assert events[-1]["detail"]["related"] is False
    assert len(events[-1]["detail"]["deviations"]) == 1


@pytest.mark.asyncio
async def test_generate_course_from_article_mocked_stages(tutor_config) -> None:
    import uuid

    course = load_service_module("app.domain.course_from_article")
    article = (
        "# pathlib\n\n"
        "## Basics\nPath wraps filesystem paths. Use `/` to join.\n\n"
        "## Name and stem\n`.name` is the final component; `.stem` drops suffix.\n"
    )
    body = CourseFromArticleRequest(
        article=article,
        title="Pathlib crash course",
        locale="ru",
        audience="middle Python",
        quiz_count=3,
        code_count=3,
    )

    stage_responses = {
        "analyze": {
            "title": "Pathlib crash course",
            "pack_id": "pathlib-crash",
            "locale": "ru",
            "domain": "code",
            "outcomes": ["join paths safely"],
            "chapters": [
                {
                    "id": "basics",
                    "title": "Basics",
                    "source_excerpt": "Path wraps filesystem paths.",
                },
            ],
        },
        "theory": {
            "id": "theory-basics",
            "title": "Basics expanded",
            "content": "Когда путь — это строка, легко ошибиться.",
        },
        "quizzes": {
            "quizzes": [
                {
                    "id": f"quiz-{i}",
                    "title": f"Q{i}",
                    "question": f"Question {i}?",
                    "choices": ["a", "b", "c", "d"],
                    "answer": i % 4,
                }
                for i in range(1, 4)
            ]
        },
        "code": {
            "tasks": [
                {
                    "id": f"code-{level}",
                    "level": level,
                    "title": f"Task {level}",
                    "content": f"Solve {level}",
                    "template": "def solve(x: int) -> int:\n    return x\n",
                    "tests": [{"input": [1], "output": 1}, {"input": [2], "output": 2}],
                }
                for level in ("easy", "medium", "hard")
            ]
        },
    }

    async def fake_stage_json(*_args, stage: str, user_message: str = "", **_kwargs):
        if stage == "theory":
            return dict(stage_responses["theory"])
        if stage == "code":
            level = "easy"
            if "## Level\n" in user_message:
                level = user_message.split("## Level\n", 1)[1].split("\n", 1)[0].strip()
            task = next(item for item in stage_responses["code"]["tasks"] if item["level"] == level)
            return {"tasks": [dict(task)]}
        if stage == "quizzes":
            index = 1
            if "## Quiz position\n" in user_message:
                pos = user_message.split("## Quiz position\n", 1)[1].split("\n", 1)[0]
                index = int(pos.split("/", 1)[0])
            quiz = stage_responses["quizzes"]["quizzes"][index - 1]
            return {"quizzes": [dict(quiz)]}
        if stage == "analyze":
            if "## Chapter position\n" in user_message:
                return {
                    "chapter": {
                        "id": "basics",
                        "title": "Basics",
                        "purpose": "Foundations",
                        "source_excerpt": "Path wraps filesystem paths.",
                    }
                }
            return dict(stage_responses["analyze"])
        if stage == "polish":
            return {"edits": []}
        return stage_responses[stage]

    with (
        patch.object(
            course,
            "fetch_user_settings",
            new=AsyncMock(
                return_value=AsyncMock(
                    provider_url="http://ollama:11434/v1",
                    api_key_encrypted=None,
                    model="qwen2.5:7b",
                )
            ),
        ),
        patch.object(course, "resolve_llm_target", return_value=_fake_llm_target()),
        patch.object(course, "is_ollama_target", return_value=True),
        patch.object(course, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)),
        patch.object(
            _theory_expand_mod(),
            "complete_text_until_done",
            new=AsyncMock(return_value=str(stage_responses["theory"]["content"])),
        ),
    ):
        response = await course.generate_course_from_article(
            AsyncMock(),
            tutor_config,
            user_id=uuid.uuid4(),
            body=body,
        )

    assert response.manifest["id"] == "pathlib-crash"
    assert collect_manifest_errors(response.manifest) == []
    assert response.meta.article_count == 1


@pytest.mark.asyncio
async def test_external_theory_mid_chapters_preserve_order(tutor_config) -> None:
    import uuid

    course = load_service_module("app.domain.course_from_article")
    body = CourseFromArticleRequest(
        article=("Path helps with files. " * 20),
        title="Path book",
        locale="ru",
        layout="phased",
        quiz_count=3,
        code_count=3,
    )
    chapters = [
        {"id": f"ch-{i}", "title": f"Chapter {i}", "source_excerpt": f"excerpt {i}"}
        for i in range(1, 5)
    ]

    async def fake_stage_json(*_args, stage: str, user_message: str = "", **_kwargs):
        await asyncio.sleep(0)
        if stage == "analyze":
            if "## Chapter position\n" in user_message:
                pos = user_message.split("## Chapter position\n", 1)[1].split("\n", 1)[0]
                index = int(pos.split("/", 1)[0])
                ch = chapters[index - 1]
                return {
                    "chapter": {
                        **ch,
                        "purpose": f"purpose {index}",
                        "source_excerpt": ch["source_excerpt"],
                    }
                }
            return {
                "title": "Path book",
                "pack_id": "path-book",
                "locale": "ru",
                "domain": "code",
                "outcomes": ["use Path"],
                "book_spine": {
                    "voice": "calm",
                    "address": "ты",
                    "throughline": "Path as a map",
                    "glossary": [{"term": "Path", "sense": "map"}],
                    "recurring_metaphors": ["map"],
                },
                "chapters": [{"id": c["id"], "title": c["title"]} for c in chapters],
            }
        if stage == "theory":
            marker = "## This chapter\n"
            assert marker in user_message
            line = user_message.split(marker, 1)[1].split("\n", 1)[0]

            title = line.split(":", 1)[1].strip()
            return {
                "id": f"theory-{title.lower().replace(' ', '-')}",
                "title": title,
                "content": f"Prose for {title}. " + ("x" * 80),
            }
        if stage == "quizzes":
            index = 1
            if "## Quiz position\n" in user_message:
                pos = user_message.split("## Quiz position\n", 1)[1].split("\n", 1)[0]
                index = int(pos.split("/", 1)[0])
            return {
                "quizzes": [
                    {
                        "id": f"quiz-{index}",
                        "title": f"Q{index}",
                        "question": f"Question {index}?",
                        "choices": ["a", "b", "c", "d"],
                        "answer": 0,
                    }
                ]
            }
        if stage == "code":
            level = "easy"
            if "## Level\n" in user_message:
                level = user_message.split("## Level\n", 1)[1].split("\n", 1)[0].strip()
            return {
                "tasks": [
                    {
                        "id": f"code-{level}",
                        "level": level,
                        "title": f"Task {level}",
                        "content": f"Solve {level}",
                        "template": "def solve(x: int) -> int:\n    return x\n",
                        "tests": [{"input": [1], "output": 1}, {"input": [2], "output": 2}],
                    }
                ]
            }
        if stage == "polish":
            return {"edits": []}
        raise AssertionError(stage)

    with (
        patch.object(
            course,
            "fetch_user_settings",
            new=AsyncMock(
                return_value=AsyncMock(
                    provider_url="https://api.openai.com/v1",
                    api_key_encrypted="x",
                    model="gpt-4o-mini",
                )
            ),
        ),
        patch.object(course, "resolve_llm_target", return_value=_fake_llm_target()),
        patch.object(course, "is_ollama_target", return_value=False),
        patch.object(course, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)),
        patch.object(
            _theory_expand_mod(),
            "complete_text_until_done",
            new=AsyncMock(return_value="Path helps with files in theory chapters."),
        ),
    ):
        response = await course.generate_course_from_article(
            AsyncMock(),
            tutor_config,
            user_id=uuid.uuid4(),
            body=body,
        )

    study = response.manifest["topics"][0]["phases"]["study"]["steps"]
    assert study[:4] == [
        "theory-chapter-1",
        "theory-chapter-2",
        "theory-chapter-3",
        "theory-chapter-4",
    ]
    assert collect_manifest_errors(response.manifest) == []


def test_sse_event_format() -> None:
    course = load_service_module("app.domain.course_from_article")
    frame = course._sse_event({"type": "stage", "stage": "analyze", "progress": 0.1})
    text = frame.decode()
    assert text.startswith("data: ")
    assert text.endswith("\n\n")
    payload = json.loads(text.removeprefix("data: ").strip())
    assert payload["stage"] == "analyze"


def test_ladder_levels_round_robin() -> None:
    practice = load_service_module("app.domain.course_from_article.practice_generate")
    assert practice._ladder_levels(0) == []
    assert practice._ladder_levels(1) == ["easy"]
    assert practice._ladder_levels(6) == [
        "easy",
        "medium",
        "hard",
        "easy",
        "medium",
        "hard",
    ]
    assert practice._ladder_levels(8) == [
        "easy",
        "medium",
        "hard",
        "easy",
        "medium",
        "hard",
        "easy",
        "medium",
    ]
    twelve = practice._ladder_levels(12)
    assert twelve.count("easy") == 4
    assert twelve.count("medium") == 4
    assert twelve.count("hard") == 4


def test_coerce_quiz_answer_accepts_string_indices() -> None:
    practice = load_service_module("app.domain.course_from_article.normalize_practice")
    assert practice._coerce_quiz_answer("2") == 2
    assert practice._coerce_quiz_answer("b") == 1
    assert practice._coerce_quiz_answer(2.0) == 2
    assert practice._coerce_quiz_answer(True) is None
    quizzes = practice._normalize_quizzes(
        [
            {
                "id": "quiz-1",
                "title": "Q",
                "question": "?",
                "choices": ["a", "b", "c", "d"],
                "answer": "1",
            }
        ],
        count=1,
    )
    assert quizzes[0]["answer"] == 1


def test_analyze_outline_max_tokens_scales_with_chapter_cap() -> None:
    analyze = load_service_module("app.domain.course_from_article.pipeline_analyze")
    small = analyze._analyze_outline_max_tokens(compact=False, chapter_cap=6)
    large = analyze._analyze_outline_max_tokens(compact=False, chapter_cap=40)
    assert large > small
    assert large >= 2400 + 40 * 90


@pytest.mark.asyncio
async def test_generate_code_tasks_one_llm_call_per_level() -> None:
    practice = load_service_module("app.domain.course_from_article.practice_generate")
    body = CourseFromArticleRequest(
        article="Path helps with files. " * 20,
        title="Path",
        locale="ru",
        code_count=3,
    )
    calls: list[str] = []

    async def fake_stage_json(*_args, stage: str, user_message: str = "", **_kwargs):
        assert stage == "code"
        level = user_message.split("## Level\n", 1)[1].split("\n", 1)[0].strip()
        calls.append(level)
        return {
            "tasks": [
                {
                    "id": f"code-{level}",
                    "level": level,
                    "title": f"Task {level}",
                    "content": f"Solve {level}",
                    "template": "def solve(x: int) -> int:\n    return x\n",
                    "tests": [{"input": [1], "output": 1}],
                }
            ]
        }

    with patch.object(practice, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)):
        tasks = await practice.generate_code_tasks(
            AsyncMock(),
            object(),
            body=body,
            compact=True,
            chapters=[{"id": "c1", "title": "Intro", "source_excerpt": "x"}],
            outcomes=["use Path"],
        )

    assert calls == ["easy", "medium", "hard"]
    assert [t["level"] for t in tasks] == ["easy", "medium", "hard"]


def test_normalize_code_tasks_accepts_alt_fields_and_llm_only() -> None:
    practice = load_service_module("app.domain.course_from_article.normalize_practice")
    tasks = practice._normalize_code_tasks(
        [
            {
                "id": "alt",
                "title": "Alt fields",
                "content": "Implement abc.ABC",
                "starter_code": "from abc import ABC\n\nclass Base(ABC):\n    pass\n",
                "test_cases": [{"input": [], "output": None}],
            },
            {
                "id": "llm-only",
                "title": "No tests",
                "content": "Explain and sketch a registry pattern",
                "code": "def register(name: str) -> None:\n    ...\n",
                "tests": [],
            },
        ],
        count=2,
        runtime="python",
        runtime_version="3.12",
    )
    assert len(tasks) == 2
    assert tasks[0]["template"].startswith("from abc")
    assert tasks[0]["tests"]
    assert tasks[1]["checker"] == "llm"
    assert tasks[1]["tests"] == []


def test_normalize_code_tasks_moves_dependencies_out_of_content() -> None:
    practice = load_service_module("app.domain.course_from_article.normalize_practice")
    tasks = practice._normalize_code_tasks(
        [
            {
                "id": "deps",
                "title": "HTTP client",
                "content": (
                    "Fetch a URL.\n\n"
                    "### Пример зависимости в requirements.txt\n"
                    "```text\nrequests==2.31.0\n```"
                ),
                "template": (
                    "import requests\n\n"
                    "def fetch(url: str) -> int:\n"
                    "    return requests.get(url).status_code\n"
                ),
                "tests": [{"input": ["https://example.com"], "output": 200}],
                "dependencies": ["requests==2.31.0"],
            },
        ],
        count=1,
        runtime="python",
        runtime_version="3.12",
    )
    assert len(tasks) == 1
    step = tasks[0]
    assert step.get("dependencies") == ["requests==2.31.0"]
    assert "requirements.txt" not in str(step.get("content"))
    assert "requests==2.31.0" not in str(step.get("content"))


@pytest.mark.asyncio
async def test_generate_code_tasks_retries_then_succeeds() -> None:
    practice = load_service_module("app.domain.course_from_article.practice_generate")
    body = CourseFromArticleRequest(
        article="Path helps with files. " * 20,
        title="Path",
        locale="ru",
        code_count=1,
    )
    calls: list[str] = []

    async def fake_stage_json(*_args, user_message: str = "", **_kwargs):
        calls.append("repair" if "## Repair" in user_message else "first")
        if "## Repair" not in user_message:
            return {"tasks": [{"title": "broken", "content": "no template"}]}
        return {
            "tasks": [
                {
                    "id": "code-easy",
                    "level": "easy",
                    "title": "Fixed",
                    "content": "Solve easy",
                    "template": "def solve(x: int) -> int:\n    return x\n",
                    "tests": [{"input": [1], "output": 1}],
                }
            ]
        }

    with patch.object(practice, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)):
        tasks = await practice.generate_code_tasks(
            AsyncMock(),
            object(),
            body=body,
            compact=False,
            chapters=[{"id": "c1", "title": "Intro", "source_excerpt": "x"}],
            outcomes=["use Path"],
        )

    assert calls == ["first", "repair"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Fixed"


@pytest.mark.asyncio
async def test_generate_code_tasks_compact_fallback_scaffold() -> None:
    practice = load_service_module("app.domain.course_from_article.practice_generate")
    body = CourseFromArticleRequest(
        article="ABC module helps define interfaces. " * 20,
        title="abc",
        locale="ru",
        code_count=1,
    )

    async def fake_stage_json(*_args, **_kwargs):
        return {"tasks": [{"title": "empty", "content": "still no code"}]}

    with patch.object(practice, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)):
        tasks = await practice.generate_code_tasks(
            AsyncMock(),
            object(),
            body=body,
            compact=True,
            chapters=[{"id": "c1", "title": "Abstract base", "source_excerpt": "x"}],
            outcomes=["use abc"],
        )

    assert len(tasks) == 1
    assert tasks[0]["checker"] == "llm"
    assert tasks[0]["template"]
    assert tasks[0]["level"] == "easy"


@pytest.mark.asyncio
async def test_generate_quizzes_one_llm_call_per_item() -> None:
    quiz_mod = load_service_module("app.domain.course_from_article.quiz_generate")
    body = CourseFromArticleRequest(
        article="Path helps with files. " * 20,
        title="Path",
        locale="ru",
        quiz_count=3,
    )
    calls: list[int] = []

    async def fake_stage_json(*_args, stage: str, user_message: str = "", **_kwargs):
        assert stage == "quizzes"
        pos = user_message.split("## Quiz position\n", 1)[1].split("\n", 1)[0]
        index = int(pos.split("/", 1)[0])
        calls.append(index)
        return {
            "quiz": {
                "id": f"quiz-{index}",
                "title": f"Q{index}",
                "question": f"Question {index}?",
                "choices": ["a", "b", "c", "d"],
                "answer": 0,
            }
        }

    with patch.object(quiz_mod, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)):
        quizzes = await quiz_mod.generate_quizzes(
            AsyncMock(),
            object(),
            body=body,
            compact=True,
            chapters=[{"id": "c1", "title": "Intro", "source_excerpt": "x"}],
            outcomes=["use Path"],
            theory_steps=[{"title": "Intro", "content": "Path wraps paths."}],
        )

    assert calls == [1, 2, 3]
    assert [q["id"] for q in quizzes] == ["quiz-1", "quiz-2", "quiz-3"]


@pytest.mark.asyncio
async def test_generate_quizzes_retries_invalid_payload() -> None:
    quiz_mod = load_service_module("app.domain.course_from_article.quiz_generate")
    body = CourseFromArticleRequest(
        article="Path helps with files. " * 20,
        title="Path",
        locale="ru",
        quiz_count=1,
    )
    attempts = {"n": 0}

    async def fake_stage_json(*_args, **_kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return {"quiz": {"title": "bad", "question": "?", "choices": ["a"], "answer": "x"}}
        return {
            "quiz": {
                "id": "quiz-1",
                "title": "Ok",
                "question": "Works?",
                "choices": ["a", "b", "c", "d"],
                "answer": "0",
            }
        }

    with patch.object(quiz_mod, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)):
        quizzes = await quiz_mod.generate_quizzes(
            AsyncMock(),
            object(),
            body=body,
            compact=True,
            chapters=[{"id": "c1", "title": "Intro", "source_excerpt": "x"}],
            outcomes=["use Path"],
            theory_steps=[{"title": "Intro", "content": "Path wraps paths."}],
        )

    assert attempts["n"] == 2
    assert quizzes[0]["answer"] == 0


def test_retarget_code_fences_fixes_python_mislabeled_as_sql() -> None:
    course = load_service_module("app.domain.course_from_article")
    md = """## Unit of Work

```sql
with Session(engine) as session:
    order = Order(user_id=1, total=500)
    session.add(order)
    session.commit()
```

```text
order = Order(user_id=1, total=100)
session.add(order)
session.flush()
```

```sql
SELECT id FROM orders WHERE total > 100
```
"""
    fixed = course._retarget_code_fences(md)
    assert "```python\nwith Session" in fixed
    assert "```python\norder = Order" in fixed
    assert "```sql\nSELECT id FROM orders" in fixed


def test_repair_code_fences_treats_lang_closer_as_close() -> None:
    course = load_service_module("app.domain.course_from_article")
    md = """#### Создание сети

```bash
docker network create my-network
```text

Эта команда создаёт сеть.

```bash
docker run --network my-network postgres
```text
"""
    fixed = course._repair_code_fences(md)
    assert "```bash\ndocker network create my-network\n```\n" in fixed
    assert "```text\n\nЭта" not in fixed
    assert fixed.count("```") % 2 == 0
    assert "Эта команда создаёт сеть." in fixed
    retargeted = course._retarget_code_fences(md)
    assert "```bash\ndocker network create my-network\n```" in retargeted


def test_repair_code_fences_fixes_double_backtick_corruption() -> None:
    course = load_service_module("app.domain.course_from_article")
    md = """Модель:

``python
class Post(models.Model):
    title = models.CharField(max_length=200)
``

Шаблон:

``html
<h1>Статьи</h1>
{% for post in posts %}
<li>{{ post.title }}</li>
{% endfor %}
``
"""
    fixed = course._repair_code_fences(md)
    assert "```python\nclass Post" in fixed
    assert "```html\n<h1>Статьи</h1>" in fixed
    assert fixed.count("```") % 2 == 0
    retargeted = course._retarget_code_fences(md)
    assert "```python\nclass Post" in retargeted
    assert "```html\n<h1>" in retargeted


def test_repair_code_fences_unwraps_indented_fences() -> None:
    course = load_service_module("app.domain.course_from_article")
    md = """Фундамент.

   ```python
   class Article(models.Model):
       title = models.CharField(max_length=200)
   ```
"""
    fixed = course._repair_code_fences(md)
    assert "```python\n   class Article" in fixed or "```python\nclass Article" in fixed
    assert fixed.strip().endswith("```")


def test_normalize_theory_step_retargets_fences() -> None:
    course = load_service_module("app.domain.course_from_article")
    step = course._normalize_theory_step(
        {
            "id": "theory-flush",
            "title": "flush",
            "content": "```sql\nwith Session(engine) as session:\n    session.flush()\n```",
        },
        {"id": "flush", "title": "flush", "source_excerpt": "excerpt"},
    )
    assert "```python\nwith Session" in str(step["content"])


def test_retarget_heals_premature_python_fence_close() -> None:
    course = load_service_module("app.domain.course_from_article")
    md = """Пример:

```python
class FieldDescriptor:
    def __init__(self, field_type):
        self.field_type = field_type

    def __get__(self, instance, owner):
        return self.value
```

def __set__(self, instance, value):
    if not isinstance(value, self.field_type):
        raise TypeError("bad")
    self.value = value

class User:
    name = FieldDescriptor(str)
```

Дальше объясняется идея.
"""
    fixed = course._retarget_code_fences(md)
    assert "def __set__(self, instance, value):" in fixed
    outside = re.sub(r"```[\s\S]*?```", "", fixed)
    assert "__set__" not in outside
    assert "Дальше объясняется идея." in outside
    assert fixed.count("```") % 2 == 0
