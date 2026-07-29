from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from app.config import GradingSettings
from app.domain.check import CheckOutcome, grade_code, grade_quiz


def _settings(*, llm: bool = True) -> GradingSettings:
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
        llm_grade_enabled=llm,
        llm_grade_min_confidence=0.65,
        secrets_master_key=None,
    )


@pytest.mark.asyncio
async def test_grade_quiz_uses_llm_when_no_answer_key(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_llm(*_args: object, **_kwargs: object) -> CheckOutcome:
        return CheckOutcome(
            passed=True,
            score=1.0,
            feedback="Correct option selected",
            details={"gradable": True, "checker": "llm", "confidence": 0.9},
            checker="llm",
            duration_ms=12,
        )

    monkeypatch.setattr("app.domain.llm.grade.try_llm_grade", _fake_llm)
    user_id = __import__("uuid").uuid4()
    outcome = await grade_quiz(
        {
            "kind": "quiz",
            "title": "SELECT",
            "choices": ["A", "B"],
            "content": {"text": "What does SELECT do?"},
        },
        {"choice_index": 0},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
        user_id=user_id,
    )
    assert outcome.passed is True
    assert outcome.checker == "llm"
    assert outcome.details.get("gradable") is True


@pytest.mark.asyncio
async def test_grade_code_uses_llm_when_no_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_llm(*_args: object, **_kwargs: object) -> CheckOutcome:
        return CheckOutcome(
            passed=False,
            score=0.0,
            feedback="Missing required columns",
            details={"gradable": True, "checker": "llm", "confidence": 0.8},
            checker="llm",
            duration_ms=20,
        )

    monkeypatch.setattr("app.domain.llm.grade.try_llm_grade", _fake_llm)
    monkeypatch.setattr("app.domain.sql.grade.looks_like_sql_step", lambda _step: False)
    user_id = __import__("uuid").uuid4()
    outcome = await grade_code(
        {"kind": "code", "title": "Names", "content": {"text": "Select name from cadets"}},
        {"source": "SELECT * FROM cadets"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
        user_id=user_id,
    )
    assert outcome.passed is False
    assert outcome.checker == "llm"
    assert outcome.details.get("gradable") is True


@pytest.mark.asyncio
async def test_llm_disabled_keeps_ungradable() -> None:
    outcome = await grade_quiz(
        {"kind": "quiz", "choices": ["A", "B"]},
        {"choice_index": 0},
        settings=_settings(llm=False),
        client=AsyncMock(spec=httpx.AsyncClient),
        user_id=__import__("uuid").uuid4(),
    )
    assert outcome.passed is False
    assert outcome.details.get("gradable") is False


@pytest.mark.asyncio
async def test_soft_accepts_mid_confidence() -> None:
    class _Resp:
        is_error = False

        def json(self) -> dict[str, object]:
            return {
                "passed": True,
                "confidence": 0.58,
                "feedback": "likely correct",
                "usable": True,
                "model": "test",
            }

    client = AsyncMock(spec=httpx.AsyncClient)
    client.post = AsyncMock(return_value=_Resp())
    from app.domain.llm.grade import try_llm_grade

    outcome = await try_llm_grade(
        client,
        _settings(),
        step={"kind": "quiz", "title": "Q"},
        submission={"choice_index": 0},
        kind="quiz",
        user_id=None,
        started=__import__("time").perf_counter(),
    )
    assert outcome is not None
    assert outcome.details.get("soft_accept") is True
    assert outcome.passed is True
