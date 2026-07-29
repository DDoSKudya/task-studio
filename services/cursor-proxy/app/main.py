from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.app import register_ops_routes
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.otel import configure_otel

from app.api.openai_api.router import router as openai_router
from app.config import load_config


def build_app() -> FastAPI:
    configure_logging("cursor-proxy")
    log = structlog.get_logger("cursor-proxy")
    config = load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient() as http_client:
            app.state.config = config
            app.state.http = http_client
            log.info("service_started", poll_based=True)
            yield
            log.info("service_stopped")

    app = FastAPI(title="cursor-proxy", lifespan=lifespan)
    register_request_id_middleware(app)
    configure_otel("cursor-proxy", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(openai_router, prefix="/v1")
    return app


app = build_app()
