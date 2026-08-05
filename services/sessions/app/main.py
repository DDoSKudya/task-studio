from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import httpx
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from studio_common.app import register_ops_routes
from studio_common.db import create_engine, create_session_factory
from studio_common.logging import configure_logging
from studio_common.middleware import register_request_id_middleware
from studio_common.migrations import ensure_schema, upgrade_head
from studio_common.otel import configure_otel

from app.api.router import router as sessions_router
from app.config import load_settings
from app.domain import messaging as session_messaging
from app.domain.sessions import SessionError

_OUTBOX_FLUSH_SEC = 30.0


def build_app() -> FastAPI:
    configure_logging("sessions")
    log = structlog.get_logger("sessions")
    sessions_settings = load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine()
        if engine is not None:
            await ensure_schema(engine, "sessions")
            await upgrade_head()
            factory = create_session_factory(engine)
            app.state.db_session_factory = factory
            session_messaging.bind_session_factory(factory)

        async def flush_outbox_loop() -> None:
            while True:
                try:
                    await session_messaging.flush_analytics_outbox(sessions_settings)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "analytics_outbox_flush_failed",
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )
                await asyncio.sleep(_OUTBOX_FLUSH_SEC)

        outbox_task = asyncio.create_task(flush_outbox_loop())
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=600.0, write=120.0, pool=10.0)
        ) as client:
            app.state.sessions_upstream_client = client
            app.state.sessions_settings = sessions_settings
            log.info("service_started")
            try:
                yield
            finally:
                outbox_task.cancel()
                with suppress(asyncio.CancelledError):
                    await outbox_task
                session_messaging.bind_session_factory(None)
                if engine is not None:
                    await engine.dispose()
                log.info("service_stopped")

    app = FastAPI(title="sessions", lifespan=lifespan)

    @app.exception_handler(SessionError)
    async def session_error(_request: Request, exc: SessionError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    register_request_id_middleware(app)
    configure_otel("sessions", app)
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    register_ops_routes(app, log)
    app.include_router(sessions_router)
    return app


app = build_app()
