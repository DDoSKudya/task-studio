from __future__ import annotations

import clickhouse_connect
from app.config import AnalyticsSettings
from app.infra.clickhouse_queries import fetch_daily_progress, insert_event
from app.infra.clickhouse_schema import (
    DAILY_PROGRESS_MV,
    DAILY_PROGRESS_MV_DDL,
    LEARNING_EVENTS_DDL,
    STUDY_SKIP_MV,
    STUDY_SKIP_MV_DDL,
)
from clickhouse_connect.driver.client import Client

__all__ = [
    "clickhouse_client",
    "ensure_schema",
    "insert_event",
    "fetch_daily_progress",
]


def clickhouse_client(settings: AnalyticsSettings) -> Client:
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


def ensure_schema(client: Client, database: str) -> None:
    client.command(f"CREATE DATABASE IF NOT EXISTS {database}")
    client.command(LEARNING_EVENTS_DDL.format(database=database))
    client.command(DAILY_PROGRESS_MV_DDL.format(database=database))
    client.command(DAILY_PROGRESS_MV.format(database=database))
    client.command(STUDY_SKIP_MV_DDL.format(database=database))
    client.command(STUDY_SKIP_MV.format(database=database))
