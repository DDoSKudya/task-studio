from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from app.config import GradingSettings
from app.domain.check import GradingError, grade_quiz


def _settings() -> GradingSettings:
    return GradingSettings(
        piston_url="http://piston:2000",
        piston_timeout_seconds=10,
        rabbitmq_url="",
        grading_jobs_queue="grading.jobs",
        lab_jobs_queue="lab.jobs",
        catalog_service_url="http://catalog:8002",
        sessions_service_url="http://sessions:8003",
        auth_service_url="http://auth:8001",
        tutor_service_url="http://tutor:8006",
        media_service_url="http://media:8009",
        packs_root="/data/packs",
        llm_grade_enabled=False,
        llm_grade_min_confidence=0.65,
        secrets_master_key=None,
    )


@pytest.mark.asyncio
async def test_grade_quiz_passes_correct_choice() -> None:
    outcome = await grade_quiz(
        {"kind": "quiz", "answer": 2},
        {"choice_index": 2},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is True
    assert outcome.score == 1.0


@pytest.mark.asyncio
async def test_grade_quiz_fails_wrong_choice() -> None:
    outcome = await grade_quiz(
        {"kind": "quiz", "answer": 2},
        {"choice_index": 0},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is False
    assert outcome.score == 0.0
    assert outcome.details.get("expected") == 2


@pytest.mark.asyncio
async def test_grade_quiz_accepts_string_answer_key() -> None:
    outcome = await grade_quiz(
        {"kind": "quiz", "answer": "1"},
        {"choice_index": 0},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is False
    assert outcome.details.get("expected") == 1


@pytest.mark.asyncio
async def test_grade_quiz_requires_choice_index() -> None:
    with pytest.raises(GradingError, match="choice_index"):
        await grade_quiz(
            {"kind": "quiz", "answer": 1},
            {},
            settings=_settings(),
            client=AsyncMock(spec=httpx.AsyncClient),
        )


@pytest.mark.asyncio
async def test_grade_quiz_missing_answer_does_not_auto_pass() -> None:
    outcome = await grade_quiz(
        {"kind": "quiz", "choices": ["A", "B"]},
        {"choice_index": 0},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is False
    assert outcome.feedback == "answer key unavailable"
    assert outcome.details.get("gradable") is False


@pytest.mark.asyncio
async def test_grade_quiz_stepik_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_creds(*_args: object, **_kwargs: object) -> dict[str, str]:
        return {}

    async def _fake_stepik(
        *_args: object, **_kwargs: object
    ) -> tuple[bool, None, dict[str, object]]:
        return True, None, {"checker": "stepik", "gradable": True}

    monkeypatch.setattr("app.domain.quiz_grade.fetch_stepik_credentials", _fake_creds)
    monkeypatch.setattr("app.domain.quiz_grade.grade_via_stepik", _fake_stepik)

    outcome = await grade_quiz(
        {
            "kind": "quiz",
            "source_platform": "stepik",
            "external_step_id": "13940",
            "choices": ["A", "B"],
        },
        {"choice_index": 1},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is True
    assert outcome.checker == "stepik"
