from __future__ import annotations

import pytest
from app.domain.course_from_article.quality.chapter_quality import (
    TheoryCritique,
    _heuristic_critique,
    _merge_critiques,
    _parse_critique,
    _soft_fail_critique,
    theory_content_is_usable,
)


def test_heuristic_critique_flags_short_draft() -> None:
    chapter = {
        "id": "ch1",
        "title": "Routers",
        "source_excerpt": "APIRouter composition and package layout. " * 40,
    }
    critique = _heuristic_critique(chapter, "Too short.")
    assert critique.ok is False
    assert critique.must_fix


def test_heuristic_critique_accepts_grounded_draft() -> None:
    excerpt = (
        "FastAPI projects should split routers with APIRouter. "
        "Keep models away from main.py to avoid cyclic imports. "
        "Package layout with routers, schemas, and services keeps imports acyclic."
    )
    draft = (
        "# Routers\n\n"
        "Use APIRouter to split routes by package. "
        "Keep models out of main.py so imports stay acyclic. "
        "Compose the app from small modules instead of one file.\n\n"
        "## Layout\n\n"
        "Place schemas next to routers and services so FastAPI packages do not cycle. "
        "The excerpt emphasizes package layout with routers, schemas, and services. "
        "Teach the learner to move handlers out of main and register routers on the app. "
        "Show why cyclic imports appear when models live beside the entrypoint.\n\n"
        "## Practice cue\n\n"
        "After splitting, the main module only creates the FastAPI app and includes routers."
    )
    chapter = {"id": "ch1", "title": "Routers", "source_excerpt": excerpt * 8}
    critique = _heuristic_critique(chapter, draft)
    assert critique.ok is True
    assert critique.score >= 0.7


def test_parse_critique_requires_score_and_empty_fixes() -> None:
    critique = _parse_critique(
        {"ok": True, "score": 0.9, "issues": [], "must_fix": ["add example"]}
    )
    assert critique.ok is False
    assert critique.must_fix == ["add example"]


def test_merge_critiques_keeps_strictest() -> None:
    left = TheoryCritique(ok=True, score=0.9, issues=[], must_fix=[])
    right = TheoryCritique(ok=False, score=0.4, issues=["weak"], must_fix=["fix"])
    merged = _merge_critiques(left, right)
    assert merged.ok is False
    assert "fix" in merged.must_fix


def test_soft_fail_critique_preserves_ok_heuristic() -> None:
    ok = TheoryCritique(ok=True, score=0.82)
    assert _soft_fail_critique(ok).ok is True
    weak = TheoryCritique(ok=False, score=0.4, issues=["short"], must_fix=["expand"])
    soft = _soft_fail_critique(weak)
    assert soft.ok is False
    assert soft.must_fix


def test_theory_content_is_usable_matches_quality_floor() -> None:
    assert theory_content_is_usable("x" * 419) is False
    assert theory_content_is_usable("x" * 420) is True


def test_heuristic_quiz_flags_placeholder_choices() -> None:
    from app.domain.course_from_article.quality.assess_quality import _heuristic_quiz

    critique = _heuristic_quiz(
        {
            "question": "What?",
            "choices": [
                "Matches the article",
                "Opposite of the article",
                "Unrelated detail",
                "Too vague to verify",
            ],
            "answer": 0,
        }
    )
    assert critique.ok is False
    assert critique.must_fix


def test_heuristic_practice_flags_empty_template() -> None:
    from app.domain.course_from_article.quality.assess_quality import _heuristic_practice

    critique = _heuristic_practice(
        {
            "title": "Practice (easy): the article",
            "content": "Write a small python snippet that demonstrates: the article.",
            "template": "pass",
            "tests": [],
            "checker": "none",
        },
        kind="code",
    )
    assert critique.ok is False


def test_heuristic_quiz_accepts_grounded_mcq() -> None:
    from app.domain.course_from_article.quality.assess_quality import _heuristic_quiz

    critique = _heuristic_quiz(
        {
            "question": "Why keep FastAPI models out of main.py in a multi-package app?",
            "choices": [
                "To avoid cyclic imports between routers and schemas",
                "Because main.py cannot import anything",
                "Only for OpenAPI title cosmetics",
                "Models must live in the database container",
            ],
            "answer": 0,
        }
    )
    assert critique.ok is True


def test_heuristic_practice_accepts_llm_checked_code() -> None:
    from app.domain.course_from_article.quality.assess_quality import _heuristic_practice

    critique = _heuristic_practice(
        {
            "title": "Split routers by package",
            "content": "Create a tiny APIRouter module and include it from the app factory.",
            "template": (
                "from fastapi import APIRouter\n\n"
                "router = APIRouter()\n\n"
                "@router.get('/ping')\n"
                "def ping() -> dict[str, str]:\n"
                "    return {'ok': '1'}\n"
            ),
            "tests": [],
            "checker": "llm",
            "rubric": "Router mounts and returns a ping payload",
        },
        kind="code",
    )
    assert critique.ok is True


@pytest.mark.asyncio
async def test_reinforce_quiz_keeps_last_patch_when_loop_ends() -> None:

    from unittest.mock import AsyncMock, patch

    from app.domain.course_from_article.quality import assess_quality as aq
    from app.domain.llm.target import LlmTarget
    from studio_contracts.api.studio_schemas import CourseFromArticleRequest

    weak = {
        "id": "quiz-1",
        "title": "Imports",
        "question": "What?",
        "choices": ["a", "b", "c", "d"],
        "answer": 0,
    }
    strong = {
        "id": "quiz-1",
        "title": "Imports",
        "question": "Why keep FastAPI models out of main.py in a multi-package app?",
        "choices": [
            "To avoid cyclic imports between routers and schemas",
            "Because main.py cannot import anything",
            "Only for OpenAPI title cosmetics",
            "Models must live in the database container",
        ],
        "answer": 0,
    }

    async def fake_stage_json(*_args: object, **kwargs: object) -> dict[str, object]:
        message = str(kwargs.get("user_message") or "")
        if "## Mode\ncritique" in message:
            return {"ok": False, "score": 0.3, "issues": ["thin"], "must_fix": ["expand"]}
        return strong

    body = CourseFromArticleRequest(article="x" * 90, locale="en")
    target = LlmTarget("http://llm.test", None, "test", num_ctx=4096)
    with patch.object(aq, "_stage_json", new=AsyncMock(side_effect=fake_stage_json)):
        out, notes = await aq.reinforce_quiz(
            AsyncMock(),
            target,
            body=body,
            quiz=weak,
            chapters=[{"title": "Routers", "source_excerpt": "APIRouter layout"}],
            outcomes=["Split routers"],
            theory_steps=[],
            max_rounds=1,
            compact=True,
        )
    assert out["question"] == strong["question"]
    assert not any("weak after reinforce" in note for note in notes)
