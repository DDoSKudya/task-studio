from __future__ import annotations

from typing import Literal

import structlog
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
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
