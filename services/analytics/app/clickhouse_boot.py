from __future__ import annotations

import contextlib

import structlog
from clickhouse_connect.driver.client import Client
from clickhouse_connect.driver.exceptions import ClickHouseError

from app.config import AnalyticsSettings
from app.infra.clickhouse import clickhouse_client
from app.infra.clickhouse import ensure_schema as ensure_clickhouse_schema


async def open_clickhouse(
    settings: AnalyticsSettings,
    log: structlog.stdlib.BoundLogger,
) -> Client | None:
    import asyncio

    client: Client | None = None
    try:
        client = clickhouse_client(settings)
        await asyncio.to_thread(
            ensure_clickhouse_schema,
            client,
            settings.clickhouse_database,
        )
    except (ClickHouseError, OSError, ConnectionError, TimeoutError) as exc:
        log.warning("clickhouse_unavailable", error=str(exc))
        if client is not None:
            with contextlib.suppress(Exception):
                client.close()
            client = None
    return client
