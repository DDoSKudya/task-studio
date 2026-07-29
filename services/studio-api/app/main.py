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

from app.api.analytics_routes.router import router as analytics_router
from app.api.auth_routes.router import router as auth_router
from app.api.catalog_routes.router import router as catalog_router
from app.api.integrations_routes.jobs import router as integrations_jobs_router
from app.api.integrations_routes.router import router as integrations_router
from app.api.media import router as media_router
from app.api.search import router as search_router
from app.api.session_routes.router import router as sessions_router
from app.api.studio_routes.ai import router as studio_ai_router
from app.api.studio_routes.router import router as studio_router
from app.api.tutor_routes.router import router as tutor_router
from app.config import load_settings
from app.lsp_gateway.router import router as editor_router
from app.middleware.auth_middleware import register_auth_middleware


def build_app() -> FastAPI:
    configure_logging("studio-api")
    log = structlog.get_logger("studio-api")
    settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            app.state.upstream_client = client
            log.info("service_started")
            try:
                yield
            finally:
                log.info("service_stopped")

    app = FastAPI(title="studio-api", lifespan=lifespan)
    app.state.settings = settings
    register_request_id_middleware(app)
    register_auth_middleware(app)
    configure_otel("studio-api", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(auth_router)
    app.include_router(catalog_router)
    app.include_router(media_router)
    app.include_router(sessions_router)
    app.include_router(integrations_router)
    app.include_router(integrations_jobs_router)
    app.include_router(search_router)
    app.include_router(analytics_router)
    app.include_router(studio_router)
    app.include_router(studio_ai_router)
    app.include_router(tutor_router)
    app.include_router(editor_router)
    return app


app = build_app()
