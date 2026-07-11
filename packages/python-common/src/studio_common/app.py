from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from studio_common.db import create_engine, create_session_factory
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.otel import configure_otel

type ReadinessStatus = Literal["ok", "degraded"]


class StatusResponse(BaseModel):
    status: ReadinessStatus


async def ping_database(
    factory: async_sessionmaker[AsyncSession],
    log: structlog.stdlib.BoundLogger,
) -> ReadinessStatus:
    try:
        async with factory() as session:
            await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        log.warning("ready_check_failed", exc_info=True)
        return "degraded"
    return "ok"


def register_ops_routes(app: FastAPI, log: structlog.stdlib.BoundLogger) -> None:
    async def health() -> StatusResponse:
        return StatusResponse(status="ok")

    async def ready() -> StatusResponse:
        factory: async_sessionmaker[AsyncSession] | None = getattr(
            app.state,
            "db_session_factory",
            None,
        )
        if factory is None:
            return StatusResponse(status="ok")
        return StatusResponse(status=await ping_database(factory, log))

    app.add_api_route("/health", health, methods=["GET"], response_model=StatusResponse)
    app.add_api_route("/ready", ready, methods=["GET"], response_model=StatusResponse)


def create_service_app(service_name: str) -> FastAPI:
    configure_logging(service_name)
    log = structlog.get_logger(service_name)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine()
        if engine is not None:
            app.state.db_session_factory = create_session_factory(engine)
        log.info("service_started")
        try:
            yield
        finally:
            if engine is not None:
                await engine.dispose()
            log.info("service_stopped")

    app = FastAPI(title=service_name, lifespan=lifespan)
    register_request_id_middleware(app)
    configure_otel(service_name, app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    return app


def service_port(default: int) -> int:
    return int(os.getenv("PORT", str(default)))
