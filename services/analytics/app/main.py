from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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

from app.api.router import router as analytics_router
from app.config import load_settings
from app.infra.clickhouse import clickhouse_client, ensure_schema
from app.worker import start_events_worker


def _run_migrations() -> None:
    command.upgrade(Config("alembic.ini"), "head")


def build_app() -> FastAPI:
    configure_logging("analytics")
    log = structlog.get_logger("analytics")
    settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine()
        worker_task: asyncio.Task[None] | None = None
        if engine is not None:
            _run_migrations()
            app.state.db_session_factory = create_session_factory(engine)
        client = clickhouse_client(settings)
        try:
            await asyncio.to_thread(ensure_schema, client, settings.clickhouse_database)
            if engine is not None:
                worker_task = start_events_worker(
                    settings,
                    app.state.db_session_factory,
                    client,
                )
            log.info("service_started")
            yield
        finally:
            if worker_task is not None:
                worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker_task
            if engine is not None:
                await engine.dispose()
            client.close()
            log.info("service_stopped")

    app = FastAPI(title="analytics", lifespan=lifespan)

    register_request_id_middleware(app)
    configure_otel("analytics", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(analytics_router)
    return app


app = build_app()
