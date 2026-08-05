from __future__ import annotations

import asyncio
import re
from collections.abc import Callable

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

_SCHEMA_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_TRANSIENT_WAIT_SEC = (0.5, 1.0, 2.0, 4.0, 8.0)


def _is_transient_db_error(exc: BaseException) -> bool:
    if isinstance(exc, ConnectionError | TimeoutError | OSError | OperationalError | DBAPIError):
        return True
    if isinstance(exc, SQLAlchemyError):
        msg = str(exc).lower()
        return any(
            token in msg
            for token in (
                "connection refused",
                "connection reset",
                "too many connections",
                "server closed the connection",
                "could not connect",
                "timeout",
                "temporarily unavailable",
            )
        )
    cause = exc.__cause__ or exc.__context__
    return cause is not None and cause is not exc and _is_transient_db_error(cause)


async def _retry_transient(action: Callable[[], None]) -> None:
    loop = asyncio.get_running_loop()
    attempt = 0
    while True:
        try:
            await loop.run_in_executor(None, action)
            return
        except (
            ConnectionError,
            TimeoutError,
            OSError,
            OperationalError,
            DBAPIError,
            SQLAlchemyError,
        ) as exc:
            if attempt >= len(_TRANSIENT_WAIT_SEC) or not _is_transient_db_error(exc):
                raise
            wait = _TRANSIENT_WAIT_SEC[attempt]
            attempt += 1
            await asyncio.sleep(wait)


async def ensure_schema(engine: AsyncEngine, schema: str) -> None:
    if _SCHEMA_NAME.fullmatch(schema) is None:
        raise ValueError(f"invalid schema name: {schema}")

    async def _create() -> None:
        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))

    attempt = 0
    while True:
        try:
            await _create()
            return
        except (
            ConnectionError,
            TimeoutError,
            OSError,
            OperationalError,
            DBAPIError,
            SQLAlchemyError,
        ) as exc:
            if attempt >= len(_TRANSIENT_WAIT_SEC) or not _is_transient_db_error(exc):
                raise
            wait = _TRANSIENT_WAIT_SEC[attempt]
            attempt += 1
            await asyncio.sleep(wait)


async def upgrade_head(config_path: str = "alembic.ini") -> None:
    def _upgrade() -> None:
        command.upgrade(Config(config_path), "head")

    await _retry_transient(_upgrade)
