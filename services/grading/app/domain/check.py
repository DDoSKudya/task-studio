from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

import httpx
from app.config import GradingSettings
from studio_contracts.grading_schemas import GradingCheckResponse


class GradingError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    passed: bool
    score: float
    feedback: str | None
    details: dict[str, object]
    checker: str
    duration_ms: int

    def to_response(self) -> GradingCheckResponse:
        return GradingCheckResponse(
            passed=self.passed,
            score=self.score,
            feedback=self.feedback,
            details=self.details,
        )


def parse_attempt_id(submission: dict[str, object]) -> uuid.UUID:
    raw = submission.get("attempt_id")
    if not isinstance(raw, str):
        raise GradingError(422, "submission requires attempt_id")
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise GradingError(422, "invalid attempt_id") from exc


def grade_quiz(step: dict[str, object], submission: dict[str, object]) -> CheckOutcome:
    answer = step.get("answer")
    if not isinstance(answer, int) or isinstance(answer, bool):
        raise GradingError(422, "quiz step has no valid answer")

    choice = submission.get("choice_index")
    if not isinstance(choice, int) or isinstance(choice, bool):
        raise GradingError(422, "quiz submission requires choice_index")

    passed = choice == answer
    return CheckOutcome(
        passed=passed,
        score=1.0 if passed else 0.0,
        feedback=None if passed else "incorrect answer",
        details={"expected": answer, "actual": choice},
        checker="quiz",
        duration_ms=0,
    )


async def grade_code(
    step: dict[str, object],
    submission: dict[str, object],
    *,
    settings: GradingSettings,
    client: httpx.AsyncClient,
) -> CheckOutcome:
    started = time.perf_counter()
    source = submission.get("source")
    if not isinstance(source, str) or not source.strip():
        raise GradingError(422, "code submission requires source")

    tests = step.get("tests")
    if not isinstance(tests, list) or not tests:
        raise GradingError(422, "code step has no tests")

    runtime = step.get("runtime")
    runtime_version = step.get("runtime_version")
    language = runtime if isinstance(runtime, str) else "python"
    version = runtime_version if isinstance(runtime_version, str) else "3.12"

    script = _build_test_script(source, tests)
    piston_result = await _execute_piston(
        client,
        settings=settings,
        language=language,
        version=version,
        source=script,
    )
    passed = bool(piston_result["passed"])
    duration_ms = int((time.perf_counter() - started) * 1000)
    stderr = piston_result.get("stderr")
    feedback = (
        stderr
        if isinstance(stderr, str) and stderr
        else ("tests failed" if not passed else None)
    )
    return CheckOutcome(
        passed=passed,
        score=1.0 if passed else 0.0,
        feedback=feedback,
        details=piston_result,
        checker="piston",
        duration_ms=duration_ms,
    )


async def check_submission(
    step: dict[str, object],
    submission: dict[str, object],
    *,
    settings: GradingSettings,
    client: httpx.AsyncClient,
) -> CheckOutcome:
    kind = step.get("kind")
    if kind == "quiz":
        return grade_quiz(step, submission)
    if kind == "code":
        return await grade_code(step, submission, settings=settings, client=client)
    raise GradingError(422, f"unsupported step kind: {kind!r}")


def _build_test_script(source: str, tests: list[object]) -> str:
    lines = [source.rstrip(), ""]
    for index, item in enumerate(tests):
        if not isinstance(item, dict):
            continue
        args = item.get("input")
        expected = item.get("output")
        if not isinstance(args, list):
            continue
        arg_literals = ", ".join(repr(value) for value in args)
        lines.append(f"assert solve({arg_literals}) == {expected!r}, 'test {index} failed'")
    if len(lines) <= 2:
        raise GradingError(422, "code step tests are invalid")
    return "\n".join(lines)


_ENTRY_FILES: dict[str, str] = {
    "python": "main.py",
    "javascript": "main.js",
    "go": "main.go",
    "sql": "main.sql",
}


async def _execute_piston(
    client: httpx.AsyncClient,
    *,
    settings: GradingSettings,
    language: str,
    version: str,
    source: str,
) -> dict[str, object]:
    payload = {
        "language": language,
        "version": version,
        "files": [{"name": _ENTRY_FILES.get(language, "main.txt"), "content": source}],
        "run_timeout": int(settings.piston_timeout_seconds * 1000),
    }
    try:
        response = await client.post(
            f"{settings.piston_url}/api/v2/execute",
            json=payload,
            timeout=settings.piston_timeout_seconds + 2,
        )
    except httpx.HTTPError as exc:
        raise GradingError(503, "code runner unavailable") from exc

    if response.status_code >= 500:
        raise GradingError(503, "code runner failed")

    return _parse_piston_response(response.json())


def _parse_piston_response(body: object) -> dict[str, object]:
    if not isinstance(body, dict):
        raise GradingError(502, "invalid code runner response")
    run = body.get("run")
    if not isinstance(run, dict):
        raise GradingError(502, "invalid code runner response")
    code = run.get("code")
    stdout = run.get("stdout")
    stderr = run.get("stderr")
    return {
        "passed": code == 0,
        "stdout": stdout if isinstance(stdout, str) else "",
        "stderr": stderr if isinstance(stderr, str) else "",
        "exit_code": code,
    }
