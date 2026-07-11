from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis
from studio_common.app import register_ops_routes
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.otel import configure_otel

from app.api.router import router as tutor_router
from app.config import load_config
from app.domain.errors import TutorError


def _redis_from_env() -> Redis | None:
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return None
    return Redis.from_url(url, decode_responses=False)


def build_app() -> FastAPI:
    configure_logging("tutor")
    log = structlog.get_logger("tutor")
    tutor_config = load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        redis = _redis_from_env()
        async with httpx.AsyncClient(timeout=120.0) as client:
            app.state.tutor_config = tutor_config
            app.state.tutor_http_client = client
            app.state.redis = redis
            log.info("service_started")
            yield
            if redis is not None:
                await redis.aclose()
            log.info("service_stopped")

    app = FastAPI(title="tutor", lifespan=lifespan)

    @app.exception_handler(TutorError)
    async def tutor_error_handler(_request: Request, exc: TutorError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    register_request_id_middleware(app)
    configure_otel("tutor", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(tutor_router)
    return app


app = build_app()
