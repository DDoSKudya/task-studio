from __future__ import annotations

from typing import Literal

import structlog
from fastapi import FastAPI, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "ready_check_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return "degraded"
    return "ok"


def register_ops_routes(app: FastAPI, log: structlog.stdlib.BoundLogger) -> None:
    async def health() -> StatusResponse:
        return StatusResponse(status="ok")

    async def ready(response: Response) -> StatusResponse:
        factory: async_sessionmaker[AsyncSession] | None = getattr(
            app.state,
            "db_session_factory",
            None,
        )
        if factory is None:
            return StatusResponse(status="ok")
        status = await ping_database(factory, log)
        body = StatusResponse(status=status)
        if status == "degraded":
            response.status_code = 503
        return body

    app.add_api_route("/health", health, methods=["GET"], response_model=StatusResponse)
    app.add_api_route("/ready", ready, methods=["GET"], response_model=StatusResponse)
