from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from app.config import GradingSettings
from app.domain.check import grade_code, grade_quiz


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
async def test_grade_quiz_accepts_choice_alias() -> None:
    outcome = await grade_quiz(
        {"kind": "quiz", "answer": 1},
        {"choice": 1},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is True


@pytest.mark.asyncio
async def test_grade_code_routes_empty_tests_to_stepik(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_creds(*_args: object, **_kwargs: object) -> dict[str, str]:
        return {"username": "u"}

    async def _fake_stepik(
        *_args: object, **_kwargs: object
    ) -> tuple[bool, str | None, dict[str, object]]:
        return True, None, {"checker": "stepik", "gradable": True}

    monkeypatch.setattr("app.domain.code.grade.fetch_stepik_credentials", _fake_creds)
    monkeypatch.setattr("app.domain.code.grade.grade_code_via_stepik", _fake_stepik)

    outcome = await grade_code(
        {
            "kind": "code",
            "source_platform": "stepik",
            "external_step_id": "8356197",
            "runtime": "sql",
            "tests": [],
        },
        {"source": "SELECT * FROM cadets WHERE squad = 'Alpha';"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is True
    assert outcome.checker == "stepik"


@pytest.mark.asyncio
async def test_grade_code_still_requires_tests_without_stepik() -> None:
    outcome = await grade_code(
        {"kind": "code", "tests": []},
        {"source": "print(1)"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is False
    assert outcome.details.get("gradable") is False
    assert outcome.checker == "none"
