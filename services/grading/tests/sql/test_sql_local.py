from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from app.config import GradingSettings
from app.domain.check import grade_code
from app.domain.sql.local import build_sql_seed, looks_like_sql_step
from app.domain.stepik_quiz import StepikQuizError, _code_reply_candidates


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


def test_code_reply_candidates_prefer_solve_sql_for_sql_runtime() -> None:
    replies = _code_reply_candidates(
        {"runtime": "sql", "stepik_reply": "solve_sql"},
        "SELECT * FROM cadets;",
        {"dataset": {}},
    )
    assert replies == [{"solve_sql": "SELECT * FROM cadets;"}]


def test_code_reply_candidates_python_does_not_lead_with_solve_sql() -> None:
    replies = _code_reply_candidates(
        {"runtime": "python"},
        "print(1)",
        {"dataset": {"languages": ["python3"]}},
    )
    assert replies[0] == {"language": "python3", "code": "print(1)"}
    assert all("solve_sql" not in reply for reply in replies)


def test_build_sql_seed_from_html_example_table() -> None:
    seed = build_sql_seed(
        {
            "runtime": "sql",
            "body_html": (
                "<p>Таблица cadets</p>"
                "<table><tr><th>id</th><th>name</th><th>squad</th></tr>"
                "<tr><td>1</td><td>Jax</td><td>Alpha</td></tr>"
                "<tr><td>2</td><td>Nova</td><td>Beta</td></tr>"
                "</table>"
            ),
        }
    )
    assert seed is not None
    assert "CREATE TABLE cadets" in seed
    assert "INSERT INTO cadets" in seed
    assert "Jax" in seed


def test_looks_like_sql_step() -> None:
    assert looks_like_sql_step({"runtime": "sql"}) is True
    assert looks_like_sql_step({"stepik_reply": "solve_sql"}) is True
    assert looks_like_sql_step({"runtime": "python"}) is False


@pytest.mark.asyncio
async def test_grade_code_falls_back_to_sql_local_on_stepik_schema_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_creds(*_args: object, **_kwargs: object) -> dict[str, str]:
        return {}

    async def _fake_stepik(*_args: object, **_kwargs: object) -> tuple[bool, str | None, dict]:
        raise StepikQuizError(
            "Reply has invalid schema: required key not provided @ data['solve_sql']"
        )

    async def _fake_piston(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"passed": True, "stdout": "1|Jax|Alpha\n", "stderr": "", "exit_code": 0}

    monkeypatch.setattr("app.domain.code.grade.fetch_stepik_credentials", _fake_creds)
    monkeypatch.setattr("app.domain.code.grade.grade_code_via_stepik", _fake_stepik)
    monkeypatch.setattr("app.domain.sql.grade.execute_piston", _fake_piston)

    outcome = await grade_code(
        {
            "kind": "code",
            "source_platform": "stepik",
            "external_step_id": "1",
            "runtime": "sql",
            "tests": [],
            "expected_stdout": "1|Jax|Alpha\n",
            "body_html": (
                "<p>из таблицы cadets</p>"
                "<table><tr><th>id</th><th>name</th></tr>"
                "<tr><td>1</td><td>Jax</td></tr></table>"
            ),
        },
        {"source": "SELECT * FROM cadets;"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is True
    assert outcome.checker == "sql_local"
    assert outcome.details.get("offline_fallback") is True


@pytest.mark.asyncio
async def test_sql_local_without_oracle_is_ungradable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_creds(*_args: object, **_kwargs: object) -> dict[str, str]:
        return {}

    async def _fake_stepik(*_args: object, **_kwargs: object) -> tuple[bool, str | None, dict]:
        raise StepikQuizError("schema error")

    async def _fake_piston(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"passed": True, "stdout": "1\n", "stderr": "", "exit_code": 0}

    monkeypatch.setattr("app.domain.code.grade.fetch_stepik_credentials", _fake_creds)
    monkeypatch.setattr("app.domain.code.grade.grade_code_via_stepik", _fake_stepik)
    monkeypatch.setattr("app.domain.sql.grade.execute_piston", _fake_piston)

    outcome = await grade_code(
        {
            "kind": "code",
            "source_platform": "stepik",
            "external_step_id": "1",
            "runtime": "sql",
            "tests": [],
            "body_html": ("<table><tr><th>id</th></tr><tr><td>1</td></tr></table>"),
        },
        {"source": "SELECT 1;"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is False
    assert outcome.details.get("gradable") is False
