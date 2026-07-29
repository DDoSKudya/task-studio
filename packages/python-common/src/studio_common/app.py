from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from studio_common.db import create_engine, create_session_factory
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.ops_routes import StatusResponse, register_ops_routes
from studio_common.otel import configure_otel

__all__ = [
    "StatusResponse",
    "create_service_app",
    "service_port",
    "register_ops_routes",
]


def create_service_app(service_name: str) -> FastAPI:
    configure_logging(service_name)
    log = structlog.get_logger(service_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine()
        if engine is not None:
            app.state.db_session_factory = create_session_factory(engine)
        log.info("service_started")
        try:
            yield
        finally:
            if engine is not None:
                await engine.dispose()
            log.info("service_stopped")

    app = FastAPI(title=service_name, lifespan=lifespan)
    register_request_id_middleware(app)
    configure_otel(service_name, app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    return app


def service_port(default: int) -> int:
    return int(os.getenv("PORT", str(default)))
