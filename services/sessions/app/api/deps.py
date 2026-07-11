from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from app.config import SessionsSettings
from app.infra.models import PhaseProgress
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
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


def get_sessions_settings(request: Request) -> SessionsSettings:
    return request.app.state.sessions_settings


def get_upstream_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.sessions_upstream_client


async def load_progress(session: AsyncSession, session_id: uuid.UUID) -> list[PhaseProgress]:
    result = await session.execute(
        select(PhaseProgress).where(PhaseProgress.session_id == session_id)
    )
    return list(result.scalars())


type DbSession = Annotated[AsyncSession, Depends(get_db)]
type Settings = Annotated[SessionsSettings, Depends(get_sessions_settings)]
type UpstreamClient = Annotated[httpx.AsyncClient, Depends(get_upstream_client)]
