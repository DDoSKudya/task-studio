from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from app.config import GradingSettings
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state,
        "db_session_factory",
        None,
    )
    if factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        )
    return factory


async def get_db(
    factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session


def get_grading_settings(request: Request) -> GradingSettings:
    return request.app.state.grading_settings


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.grading_http_client


type DbSession = Annotated[AsyncSession, Depends(get_db)]
type Settings = Annotated[GradingSettings, Depends(get_grading_settings)]
type GradingHttpClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]
