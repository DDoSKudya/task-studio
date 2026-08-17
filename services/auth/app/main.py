from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.database.db import create_engine, create_session_factory
from studio_common.database.migrations import ensure_schema, upgrade_head
from studio_common.observability.logging import configure_logging
from studio_common.observability.otel import configure_otel
from studio_common.web.app import register_ops_routes
from studio_common.web.middleware import register_request_id_middleware

from app.api.router import router as auth_router


def build_app() -> FastAPI:
    configure_logging("auth")
    log = structlog.get_logger("auth")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine()
        if engine is not None:
            await ensure_schema(engine, "auth")
            await upgrade_head()
            app.state.db_session_factory = create_session_factory(engine)
        log.info("service_started")
        try:
            yield
        finally:
            if engine is not None:
                await engine.dispose()
            log.info("service_stopped")

    app = FastAPI(title="auth", lifespan=lifespan)
    register_request_id_middleware(app)
    configure_otel("auth", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(auth_router)
    return app


app = build_app()
