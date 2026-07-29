from __future__ import annotations

import time

import httpx
from app.domain.check.outcome import CheckOutcome, GradingError, optional_str


def _response_message(body: object) -> str | None:
    if not isinstance(body, dict):
        return None
    return optional_str(body.get("message"))


def piston_client_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return "invalid code runner response"
    if message := _response_message(body):
        return f"code runner rejected request: {message}"
    return "invalid code runner response"


def parse_piston_response(body: object) -> dict[str, object]:
    if not isinstance(body, dict):
        raise GradingError(502, "invalid code runner response")
    run = body.get("run")
    if not isinstance(run, dict):
        if message := _response_message(body):
            raise GradingError(502, f"code runner rejected request: {message}")
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


def piston_outcome(
    piston_result: dict[str, object],
    *,
    started: float,
    checker: str,
    extra_details: dict[str, object] | None = None,
) -> CheckOutcome:
    passed = bool(piston_result["passed"])
    feedback = None
    if not passed:
        feedback = (
            optional_str(piston_result.get("stderr"))
            or optional_str(piston_result.get("stdout"))
            or "tests failed"
        )
    details: dict[str, object] = {
        **piston_result,
        "gradable": True,
        "checker": checker,
    }
    if extra_details:
        details.update(extra_details)
    return CheckOutcome(
        passed=passed,
        score=1.0 if passed else 0.0,
        feedback=feedback,
        details=details,
        checker=checker,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
