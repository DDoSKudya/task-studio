from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import structlog
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.app import register_ops_routes
from studio_common.db import create_engine, create_session_factory
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.otel import configure_otel
from studio_integration_sdk.registry import discover_adapters

from app.api.router import router as integrations_router
from app.config import load_settings
from app.worker import start_import_worker


def _run_migrations() -> None:
    command.upgrade(Config("alembic.ini"), "head")


def build_app() -> FastAPI:
    configure_logging("integrations")
    log = structlog.get_logger("integrations")
    settings = load_settings()
    settings.packs_root.mkdir(parents=True, exist_ok=True)
    adapters = discover_adapters(settings.integration_modules_root)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine()
        worker_task: asyncio.Task[None] | None = None
        if engine is not None:
            _run_migrations()
            app.state.db_session_factory = create_session_factory(engine)
        async with httpx.AsyncClient(timeout=120.0) as client:
            if engine is not None:
                worker_task = start_import_worker(
                    settings,
                    app.state.db_session_factory,
                    client,
                    adapters,
                )
            log.info("service_started")
            yield
            if worker_task is not None:
                worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker_task
            if engine is not None:
                await engine.dispose()
            log.info("service_stopped")

    app = FastAPI(title="integrations", lifespan=lifespan)
    app.state.integrations_settings = settings
    app.state.adapters = adapters

    register_request_id_middleware(app)
    configure_otel("integrations", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(integrations_router)
    return app


app = build_app()
