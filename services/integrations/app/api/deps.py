from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from app.config import IntegrationsSettings
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from studio_integration_sdk.registry import AdapterModule


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


def get_settings(request: Request) -> IntegrationsSettings:
    return request.app.state.integrations_settings


def get_adapters(request: Request) -> dict[str, AdapterModule]:
    adapters: dict[str, AdapterModule] = request.app.state.adapters
    return adapters


type DbSession = Annotated[AsyncSession, Depends(get_db)]
type Settings = Annotated[IntegrationsSettings, Depends(get_settings)]
type Adapters = Annotated[dict[str, AdapterModule], Depends(get_adapters)]
