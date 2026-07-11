from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from studio_common.app import register_ops_routes
from studio_common.db import create_engine, create_session_factory
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.otel import configure_otel

from app.api.router import router as auth_router


def _run_migrations() -> None:
    command.upgrade(Config("alembic.ini"), "head")


async def _ensure_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))


def build_app() -> FastAPI:
    configure_logging("auth")
    log = structlog.get_logger("auth")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine()
        if engine is not None:
            await _ensure_schema(engine)
            _run_migrations()
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
