from __future__ import annotations

import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter


def _otlp_exporter(endpoint: str) -> SpanExporter | None:
    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-not-found]
            OTLPSpanExporter,
        )
    except ImportError:
        return None
    exporter: SpanExporter = OTLPSpanExporter(endpoint=endpoint)
    return exporter


def configure_otel(service_name: str, app: FastAPI) -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))

    if endpoint and (exporter := _otlp_exporter(endpoint)) is not None:
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
