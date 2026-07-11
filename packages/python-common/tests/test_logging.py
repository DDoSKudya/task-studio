from __future__ import annotations

import json
import logging

import pytest
import structlog
from studio_common.logging import configure_logging


def _last_log_line(capsys: pytest.CaptureFixture[str]) -> str:
    return capsys.readouterr().out.strip().split("\n")[-1]


@pytest.mark.parametrize(
    ("log_format", "expect_json"),
    [
        ("json", True),
        ("console", False),
    ],
)
def test_configure_logging_renderer(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    log_format: str,
    expect_json: bool,
) -> None:
    monkeypatch.setenv("LOG_FORMAT", log_format)
    configure_logging("studio-api")
    structlog.get_logger().info("ping")

    line = _last_log_line(capsys)
    if expect_json:
        json.loads(line)
    else:
        with pytest.raises(json.JSONDecodeError):
            json.loads(line)


def test_configure_logging_defaults_to_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    configure_logging("catalog")
    structlog.get_logger().info("ping")
    json.loads(_last_log_line(capsys))


def test_configure_logging_includes_service_and_request_id(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("LOG_FORMAT", "json")
    configure_logging("catalog")
    structlog.contextvars.bind_contextvars(request_id="trace-99")
    logging.getLogger("catalog").info("ready_check")

    payload = json.loads(_last_log_line(capsys))
    assert payload["service"] == "catalog"
    assert payload["request_id"] == "trace-99"
