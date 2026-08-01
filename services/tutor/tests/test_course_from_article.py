from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from studio_contracts.pack import collect_manifest_errors
from studio_contracts.studio_schemas import CourseArticleInput, CourseFromArticleRequest
from tutor_helpers.loaders import load_service_module


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
    assert "curriculum-synthesis" in skills
    assert "course-stage-json" in skills


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
async def test_consistency_gate_stops_without_ignore() -> None:
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
        patch.object(course, "resolve_llm_target", return_value=object()),
        patch.object(course, "is_ollama_target", return_value=True),
        patch.object(course, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)),
    ):
        events = [
            event
            async for event in course.iter_course_from_article(
                AsyncMock(),
                AsyncMock(),
                user_id=uuid.uuid4(),
                body=body,
            )
        ]

    assert events[-1]["type"] == "consistency_gate"
    assert events[-1]["detail"]["related"] is False
    assert len(events[-1]["detail"]["deviations"]) == 1


@pytest.mark.asyncio
async def test_generate_course_from_article_mocked_stages() -> None:
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
        patch.object(course, "resolve_llm_target", return_value=object()),
        patch.object(course, "is_ollama_target", return_value=True),
        patch.object(course, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)),
    ):
        response = await course.generate_course_from_article(
            AsyncMock(),
            AsyncMock(),
            user_id=uuid.uuid4(),
            body=body,
        )

    assert response.manifest["id"] == "pathlib-crash"
    assert collect_manifest_errors(response.manifest) == []
    assert response.meta.article_count == 1


@pytest.mark.asyncio
async def test_external_theory_mid_chapters_preserve_order() -> None:
    import uuid

    course = load_service_module("app.domain.course_from_article")
    body = CourseFromArticleRequest(
        article=("Path helps with files. " * 20),
        title="Path book",
        locale="ru",
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
        patch.object(course, "resolve_llm_target", return_value=object()),
        patch.object(course, "is_ollama_target", return_value=False),
        patch.object(course, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)),
    ):
        response = await course.generate_course_from_article(
            AsyncMock(),
            AsyncMock(),
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
