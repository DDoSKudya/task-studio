from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.app import register_ops_routes
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.otel import configure_otel

from app.api.router import router as media_router
from app.config import load_settings
from app.storage import build_client, ensure_bucket


def _wait_for_bucket(
    client, bucket: str, *, log, attempts: int = 30, delay_sec: float = 1.0
) -> None:

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            ensure_bucket(client, bucket)
            if attempt > 1:
                log.info("minio_ready", attempt=attempt)
            return
        except Exception as exc:  # noqa: BLE001 — boot wait; MinIO client raises urllib3/S3 variants
            last_error = exc
            log.warning("minio_not_ready", attempt=attempt, error=str(last_error))
            time.sleep(delay_sec)
    log.error("minio_unavailable", error=str(last_error))


def build_app() -> FastAPI:
    configure_logging("media")
    log = structlog.get_logger("media")
    media_settings = load_settings()
    minio_client = build_client(media_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _wait_for_bucket(minio_client, media_settings.bucket, log=log)
        log.info("service_started")
        try:
            yield
        finally:
            log.info("service_stopped")

    app = FastAPI(title="media", lifespan=lifespan)
    app.state.media_settings = media_settings
    app.state.minio_client = minio_client
    register_request_id_middleware(app)
    configure_otel("media", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(media_router)
    return app


app = build_app()
