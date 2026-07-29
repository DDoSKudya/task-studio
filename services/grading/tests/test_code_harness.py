from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from app.config import GradingSettings
from app.domain.check import grade_code
from app.domain.harness import build_exercism_job, build_fcc_job, build_io_job


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


def test_build_io_job_python_and_javascript() -> None:
    py = build_io_job(
        language="python",
        version="3.12",
        source="def solve(a, b):\n    return a + b\n",
        tests=[{"input": [2, 3], "output": 5}],
    )
    assert py.language == "python"
    assert "assert solve(2, 3) == 5" in py.files[0]["content"]

    js = build_io_job(
        language="javascript",
        version="18.15.0",
        source="function solve(a, b) { return a + b; }\n",
        tests=[{"input": [2, 3], "output": 5}],
    )
    assert js.language == "javascript"
    assert "deepStrictEqual" in js.files[0]["content"]


def test_build_io_job_infers_domain_entrypoint_from_template() -> None:
    job = build_io_job(
        language="python",
        version="3.12",
        template="def create_user_and_get_id(session, email: str) -> int:\n    pass\n",
        source=(
            "def create_user_and_get_id(session, email: str) -> int:\n"
            "    session.add(type('U', (), {'email': email, 'id': None})())\n"
            "    session.flush()\n"
            "    return 1\n"
        ),
        setup=(
            "class MockSession:\n"
            "    def add(self, obj): self.obj = obj\n"
            "    def flush(self):\n"
            "        self.obj.id = 1\n"
            "def make_session():\n"
            "    return MockSession()\n"
        ),
        tests=[{"input": [{"$call": "make_session"}, "a@b.c"], "output": 1}],
    )
    body = job.files[0]["content"]
    assert "assert create_user_and_get_id(make_session(), 'a@b.c') == 1" in body
    assert "solve(" not in body


def test_build_io_job_scripted_run_does_not_require_entrypoint() -> None:
    job = build_io_job(
        language="python",
        version="3.12",
        source="def add(a, b):\n    return a + b\n",
        tests=[{"run": "assert add(2, 3) == 5"}],
    )
    body = job.files[0]["content"]
    assert "assert add(2, 3) == 5" in body
    assert "def __run_tests():" in body


def test_build_exercism_python_job_infers_filenames() -> None:
    job = build_exercism_job(
        runtime="python",
        source="def hello():\n    return 'Hello, World!'\n",
        test_source=(
            "import unittest\n"
            "from hello_world import hello\n"
            "class T(unittest.TestCase):\n"
            "    def test_hi(self):\n"
            "        self.assertEqual(hello(), 'Hello, World!')\n"
        ),
    )
    assert job is not None
    names = {item["name"] for item in job.files}
    assert names == {"main.py", "hello_world.py", "hello_world_test.py"}


def test_build_exercism_javascript_unsupported() -> None:
    job = build_exercism_job(
        runtime="javascript",
        source="export function hello() { return 'Hello, World!'; }",
        test_source="import { hello } from './hello-world.js';",
    )
    assert job is None


def test_build_fcc_job_keeps_regex_asserts() -> None:
    job = build_fcc_job(
        runtime="javascript",
        source="// hello\nvar x = 1;\n",
        fcc_tests=[
            {
                "text": "comment",
                "test_string": "assert(code.match(/(\\/\\/)...../g));",
            },
            {
                "text": "dom",
                "test_string": "assert(document.querySelector('div'));",
            },
        ],
    )
    assert job is not None
    body = job.files[0]["content"]
    assert "code.match" in body
    assert "document.querySelector" not in body


@pytest.mark.asyncio
async def test_grade_code_exercism_python(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_piston(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"passed": True, "stdout": "ok", "stderr": "", "exit_code": 0}

    monkeypatch.setattr("app.domain.code.grade.execute_piston_job", _fake_piston)
    outcome = await grade_code(
        {
            "kind": "code",
            "runtime": "python",
            "tests": [],
            "test_source": (
                "import unittest\n"
                "from hello_world import hello\n"
                "class T(unittest.TestCase):\n"
                "    def test_hi(self):\n"
                "        self.assertEqual(hello(), 'Hello, World!')\n"
            ),
            "solution_file": "hello_world.py",
            "test_file": "hello_world_test.py",
        },
        {"source": "def hello():\n    return 'Hello, World!'\n"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is True
    assert outcome.checker == "exercism"
    assert outcome.details.get("gradable") is True


@pytest.mark.asyncio
async def test_grade_code_fcc_javascript(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_piston(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"passed": True, "stdout": "", "stderr": "", "exit_code": 0}

    monkeypatch.setattr("app.domain.code.grade.execute_piston_job", _fake_piston)
    outcome = await grade_code(
        {
            "kind": "code",
            "runtime": "javascript",
            "tests": [],
            "fcc_tests": [
                {"text": "comment", "test_string": "assert(code.match(/hello/i));"},
            ],
        },
        {"source": "// hello world\n"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is True
    assert outcome.checker == "fcc"


@pytest.mark.asyncio
async def test_grade_code_io_javascript(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_piston(*_args: object, **kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"passed": True, "stdout": "", "stderr": "", "exit_code": 0}

    monkeypatch.setattr("app.domain.code.grade.execute_piston_job", _fake_piston)
    outcome = await grade_code(
        {
            "kind": "code",
            "runtime": "javascript",
            "runtime_version": "18.15.0",
            "tests": [{"input": [1, 2], "output": 3}],
        },
        {"source": "function solve(a, b) { return a + b; }\n"},
        settings=_settings(),
        client=AsyncMock(spec=httpx.AsyncClient),
    )
    assert outcome.passed is True
    assert outcome.checker == "piston"
    job = captured.get("job")
    assert job is not None
    assert getattr(job, "language", None) == "javascript"
    files = getattr(job, "files", None)
    assert isinstance(files, list) and files
    assert "deepStrictEqual" in str(files[0].get("content"))
