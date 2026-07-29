from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from app.config import AnalyticsSettings, load_settings
from clickhouse_connect.driver.client import Client
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return request.app.state.db_session_factory


async def get_db_session(
    factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session


def get_clickhouse(request: Request) -> Client | None:
    return getattr(request.app.state, "clickhouse", None)


def get_settings() -> AnalyticsSettings:
    return load_settings()


DbSession = Annotated[AsyncSession, Depends(get_db_session)]
ClickHouseClient = Annotated[Client | None, Depends(get_clickhouse)]
Settings = Annotated[AnalyticsSettings, Depends(get_settings)]
