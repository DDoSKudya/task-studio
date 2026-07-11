from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.app import register_ops_routes
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.otel import configure_otel

from app.api.router import router as orchestrator_router


def build_app() -> FastAPI:
    configure_logging("orchestrator")
    log = structlog.get_logger("orchestrator")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        log.info("service_started")
        yield
        log.info("service_stopped")

    app = FastAPI(title="orchestrator", lifespan=lifespan)
    register_request_id_middleware(app)
    configure_otel("orchestrator", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(orchestrator_router)
    return app


app = build_app()
