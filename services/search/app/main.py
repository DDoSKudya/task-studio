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
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.otel import configure_otel

from app.api.router import router as search_router
from app.config import load_settings
from app.infra.meili import ensure_index, meili_client
from app.worker import start_index_worker


def build_app() -> FastAPI:
    configure_logging("search")
    log = structlog.get_logger("search")
    settings = load_settings()
    client = meili_client(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        worker_task: asyncio.Task[None] | None = None
        await asyncio.to_thread(
            ensure_index,
            client,
            settings.index_name,
            ollama_url=settings.ollama_url,
        )
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            worker_task = start_index_worker(settings, client, http_client)
            log.info("service_started")
            yield
            if worker_task is not None:
                worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker_task
            log.info("service_stopped")

    app = FastAPI(title="search", lifespan=lifespan)
    app.state.search_settings = settings
    app.state.meili_client = client

    register_request_id_middleware(app)
    configure_otel("search", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(search_router)
    return app


app = build_app()
