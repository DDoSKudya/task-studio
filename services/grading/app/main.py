from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import structlog
from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.app import register_ops_routes
from studio_common.db import create_engine, create_session_factory
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.otel import configure_otel

from app.api.router import router as grading_router
from app.config import load_settings
from app.domain.check import GradingError


def _run_migrations() -> None:
    command.upgrade(Config("alembic.ini"), "head")


def build_app() -> FastAPI:
    configure_logging("grading")
    log = structlog.get_logger("grading")
    grading_settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine()
        if engine is not None:
            _run_migrations()
            app.state.db_session_factory = create_session_factory(engine)
        async with httpx.AsyncClient(timeout=grading_settings.piston_timeout_seconds + 5) as client:
            app.state.grading_http_client = client
            app.state.grading_settings = grading_settings
            log.info("service_started")
            try:
                yield
            finally:
                if engine is not None:
                    await engine.dispose()
                log.info("service_stopped")

    app = FastAPI(title="grading", lifespan=lifespan)

    @app.exception_handler(GradingError)
    async def grading_error(_request: Request, exc: GradingError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    register_request_id_middleware(app)
    configure_otel("grading", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(grading_router)
    return app


app = build_app()
