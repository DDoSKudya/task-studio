from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from clickhouse_connect.driver.client import Client
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.database.db import create_engine, create_session_factory
from studio_common.database.migrations import ensure_schema as ensure_pg_schema
from studio_common.database.migrations import upgrade_head
from studio_common.observability.logging import configure_logging
from studio_common.observability.otel import configure_otel
from studio_common.web.app import register_ops_routes
from studio_common.web.middleware import register_request_id_middleware

from app.api.ingest import router as ingest_router
from app.api.router import router as analytics_router
from app.clickhouse_boot import open_clickhouse
from app.config import load_settings
from app.worker import start_events_worker


def build_app() -> FastAPI:
    configure_logging("analytics")
    log = structlog.get_logger("analytics")
    settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine()
        worker_task: asyncio.Task[None] | None = None
        client: Client | None = None
        if engine is not None:
            await ensure_pg_schema(engine, "analytics")
            await upgrade_head()
            app.state.db_session_factory = create_session_factory(engine)
        try:
            client = await open_clickhouse(settings, log)
            app.state.clickhouse = client
            if engine is not None:
                worker_task = start_events_worker(
                    settings,
                    app.state.db_session_factory,
                    client,
                )
            log.info("service_started", clickhouse=client is not None)
            yield
        finally:
            if worker_task is not None:
                worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker_task
            if engine is not None:
                await engine.dispose()
            if client is not None:
                with contextlib.suppress(Exception):
                    client.close()
            log.info("service_stopped")

    app = FastAPI(title="analytics", lifespan=lifespan)

    register_request_id_middleware(app)
    configure_otel("analytics", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(analytics_router)
    app.include_router(ingest_router)
    return app


app = build_app()
