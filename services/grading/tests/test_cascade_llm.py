from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from app.config import GradingSettings
from app.domain.check import CheckOutcome, grade_code, grade_task
from app.domain.code import grade as code_grade_mod
from app.domain.llm import grade as llm_grade_mod


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
async def test_non_executable_tests_use_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_llm(*_a: object, **_k: object) -> CheckOutcome:
        return CheckOutcome(
            passed=True,
            score=1.0,
            feedback="ok via llm",
            details={"gradable": True, "checker": "llm"},
            checker="llm",
            duration_ms=1,
        )

    monkeypatch.setattr(llm_grade_mod, "try_llm_grade", _fake_llm)
    outcome = await grade_code(
        {
            "kind": "code",
            "runtime": "python",
            "content": "Create a user and flush",
            "template": "def create_user_and_get_id(session, email): pass\n",
            "tests": [{"input": ["mock_session", "a@b.c"], "output": 1}],
        },
        {"source": "def create_user_and_get_id(session, email):\n    return 1\n"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
        user_id=uuid4(),
    )
    assert outcome.checker == "llm"
    assert outcome.passed is True


@pytest.mark.asyncio
async def test_checker_llm_skips_piston(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"piston": False}

    async def _boom(*_a: object, **_k: object) -> dict[str, object]:
        called["piston"] = True
        return {"passed": True, "stdout": "", "stderr": "", "exit_code": 0}

    async def _fake_llm(*_a: object, **_k: object) -> CheckOutcome:
        return CheckOutcome(
            passed=True,
            score=1.0,
            feedback="llm",
            details={"gradable": True, "checker": "llm"},
            checker="llm",
            duration_ms=1,
        )

    monkeypatch.setattr(code_grade_mod, "execute_piston_job", _boom)
    monkeypatch.setattr(llm_grade_mod, "try_llm_grade", _fake_llm)
    outcome = await grade_code(
        {
            "kind": "code",
            "checker": "llm",
            "runtime": "python",
            "tests": [{"input": [1], "output": 1}],
        },
        {"source": "def solve(x): return x\n"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
        user_id=uuid4(),
    )
    assert called["piston"] is False
    assert outcome.checker == "llm"


@pytest.mark.asyncio
async def test_grade_task_uses_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_llm(*_a: object, **kwargs: object) -> CheckOutcome:
        assert kwargs.get("kind") == "task"
        return CheckOutcome(
            passed=True,
            score=1.0,
            feedback="good answer",
            details={"gradable": True, "checker": "llm"},
            checker="llm",
            duration_ms=1,
        )

    monkeypatch.setattr(llm_grade_mod, "try_llm_grade", _fake_llm)
    outcome = await grade_task(
        {
            "kind": "task",
            "content": "Translate to English",
            "rubric": "- correct grammar\n- natural tone",
        },
        {"text": "Hello, how are you?"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
        user_id=uuid4(),
    )
    assert outcome.passed is True
    assert outcome.checker == "llm"


@pytest.mark.asyncio
async def test_grade_task_requires_text() -> None:
    outcome = await grade_task(
        {"kind": "task", "content": "Write something"},
        {"text": "  "},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is False
    assert outcome.checker == "none"


@pytest.mark.asyncio
async def test_unknown_kind_with_text_uses_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_llm(*_a: object, **_k: object) -> CheckOutcome:
        return CheckOutcome(
            passed=True,
            score=1.0,
            feedback="ok",
            details={"gradable": True, "checker": "llm"},
            checker="llm",
            duration_ms=1,
        )

    monkeypatch.setattr(llm_grade_mod, "try_llm_grade", _fake_llm)
    from app.domain.check import check_submission

    outcome = await check_submission(
        {"kind": "essay", "title": "Write", "content": "Explain polymorphism"},
        {"text": "Polymorphism lets one interface many forms"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
        user_id=uuid4(),
    )
    assert outcome.checker == "llm"
    assert outcome.passed is True


@pytest.mark.asyncio
async def test_lab_kind_grades_report_via_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_llm(*_a: object, **kwargs: object) -> CheckOutcome:
        assert kwargs.get("kind") == "lab"
        return CheckOutcome(
            passed=True,
            score=1.0,
            feedback="lab report ok",
            details={"gradable": True, "checker": "llm"},
            checker="llm",
            duration_ms=1,
        )

    monkeypatch.setattr(llm_grade_mod, "try_llm_grade", _fake_llm)
    from app.domain.check import check_submission

    outcome = await check_submission(
        {"kind": "lab", "title": "Nginx", "content": "Configure reverse proxy"},
        {"report": "Configured nginx and curl returned 200"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
        user_id=uuid4(),
    )
    assert outcome.checker == "llm"
    assert outcome.passed is True
