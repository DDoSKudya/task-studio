from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.database.db import create_engine, create_session_factory
from studio_common.database.migrations import ensure_schema, upgrade_head
from studio_common.observability.logging import configure_logging
from studio_common.observability.otel import configure_otel
from studio_common.web.app import register_ops_routes
from studio_common.web.middleware import register_request_id_middleware

from app.api.router import router as catalog_router
from app.config import load_settings
from app.domain.packs import PackError


def build_app() -> FastAPI:
    configure_logging("catalog")
    log = structlog.get_logger("catalog")
    catalog_settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            catalog_settings.packs_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning(
                "packs_root_unusable",
                path=str(catalog_settings.packs_root),
                error=str(exc),
            )
        engine = create_engine()
        if engine is not None:
            await ensure_schema(engine, "catalog")
            if os.getenv("CATALOG_MIGRATIONS_DONE", "").strip() != "1":
                await upgrade_head()
            app.state.db_session_factory = create_session_factory(engine)
        log.info("service_started")
        try:
            yield
        finally:
            if engine is not None:
                await engine.dispose()
            log.info("service_stopped")

    app = FastAPI(title="catalog", lifespan=lifespan)
    app.state.catalog_settings = catalog_settings

    @app.exception_handler(PackError)
    async def pack_error(_request: Request, exc: PackError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    register_request_id_middleware(app)
    configure_otel("catalog", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(catalog_router)
    return app


app = build_app()
