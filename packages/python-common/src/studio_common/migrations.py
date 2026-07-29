from __future__ import annotations

import asyncio
import re

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

_SCHEMA_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


async def ensure_schema(engine: AsyncEngine, schema: str) -> None:
    if _SCHEMA_NAME.fullmatch(schema) is None:
        raise ValueError(f"invalid schema name: {schema}")
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))


async def upgrade_head(config_path: str = "alembic.ini") -> None:
    def _upgrade() -> None:
        command.upgrade(Config(config_path), "head")

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _upgrade)
