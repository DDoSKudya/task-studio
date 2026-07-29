from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.app import register_ops_routes
from studio_common.db import create_engine, create_session_factory
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.migrations import ensure_schema, upgrade_head
from studio_common.otel import configure_otel

from app.config import load_settings
from app.worker import start_lab_worker


def build_app() -> FastAPI:
    configure_logging("lab-runner")
    log = structlog.get_logger("lab-runner")
    settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine()
        worker_task: asyncio.Task[None] | None = None
        if engine is not None:
            await ensure_schema(engine, "lab_runner")
            await upgrade_head()
            app.state.db_session_factory = create_session_factory(engine)
        async with httpx.AsyncClient(timeout=120.0) as client:
            if engine is not None:
                worker_task = start_lab_worker(settings, app.state.db_session_factory, client)
            log.info("service_started", dry_run=settings.dry_run)
            try:
                yield
            finally:
                if worker_task is not None:
                    worker_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await worker_task
                if engine is not None:
                    await engine.dispose()
                log.info("service_stopped")

    app = FastAPI(title="lab-runner", lifespan=lifespan)
    register_request_id_middleware(app)
    configure_otel("lab-runner", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    return app


app = build_app()
