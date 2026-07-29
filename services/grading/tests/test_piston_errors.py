from __future__ import annotations

import httpx
import pytest
from app.domain.check.outcome import GradingError
from app.domain.piston.client import parse_piston_response, piston_client_error


def test_parse_piston_response_success() -> None:
    result = parse_piston_response({"run": {"code": 0, "stdout": "ok\n", "stderr": ""}})
    assert result["passed"] is True
    assert result["stdout"] == "ok\n"


def test_parse_piston_response_surfaces_message() -> None:
    with pytest.raises(GradingError, match="runtime is unknown") as exc:
        parse_piston_response({"message": "python-3.12.0 runtime is unknown"})
    assert exc.value.status_code == 502


def test_piston_client_error_from_json() -> None:
    response = httpx.Response(
        400,
        json={"message": "run_timeout cannot exceed the configured limit of 3000"},
    )
    assert "run_timeout" in piston_client_error(response)
