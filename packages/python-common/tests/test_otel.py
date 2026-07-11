from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from studio_common.otel import configure_otel


def test_configure_otel_skips_exporter_without_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    with patch("studio_common.otel._otlp_exporter") as mock_exporter:
        configure_otel("auth", FastAPI())
    mock_exporter.assert_not_called()


def test_configure_otel_skips_exporter_for_blank_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "   ")
    with patch("studio_common.otel._otlp_exporter") as mock_exporter:
        configure_otel("auth", FastAPI())
    mock_exporter.assert_not_called()


def test_configure_otel_registers_tracer_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    configure_otel("sessions", FastAPI())
    assert isinstance(trace.get_tracer_provider(), TracerProvider)


def test_configure_otel_adds_exporter_when_endpoint_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel:4317")
    mock_exporter = MagicMock()
    with patch("studio_common.otel._otlp_exporter", return_value=mock_exporter) as factory:
        configure_otel("grading", FastAPI())
    factory.assert_called_once_with("http://otel:4317")
