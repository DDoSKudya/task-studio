from __future__ import annotations

import json

import clickhouse_connect
from app.config import AnalyticsSettings
from app.datetime_utils import ensure_utc
from clickhouse_connect.driver.client import Client
from studio_contracts.analytics_schemas import AnalyticsEventMessage

LEARNING_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS {database}.learning_events (
    event_time DateTime64(3, 'UTC'),
    event_id UUID,
    user_id UUID,
    session_id UUID,
    event_type LowCardinality(String),
    pack_version_id UUID,
    pack_title String,
    topic_id String,
    phase LowCardinality(String),
    step_id String,
    payload String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_time)
ORDER BY (user_id, event_time, event_type)
TTL event_time + INTERVAL 365 DAY
"""

DAILY_PROGRESS_MV_DDL = """
CREATE TABLE IF NOT EXISTS {database}.daily_user_progress_ch (
    day Date,
    user_id UUID,
    sessions_started UInt32,
    steps_completed UInt32
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(day)
ORDER BY (user_id, day)
"""

DAILY_PROGRESS_MV = """
CREATE MATERIALIZED VIEW IF NOT EXISTS {database}.daily_user_progress_mv
TO {database}.daily_user_progress_ch
AS SELECT
    toDate(event_time) AS day,
    user_id,
    countIf(event_type = 'session_started') AS sessions_started,
    countIf(event_type = 'step_completed') AS steps_completed
FROM {database}.learning_events
GROUP BY day, user_id
"""

STUDY_SKIP_MV_DDL = """
CREATE TABLE IF NOT EXISTS {database}.study_skip_counts_ch (
    day Date,
    user_id UUID,
    pack_version_id UUID,
    topic_id String,
    skip_count UInt32
) ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(day)
ORDER BY (user_id, day, pack_version_id, topic_id)
"""

STUDY_SKIP_MV = """
CREATE MATERIALIZED VIEW IF NOT EXISTS {database}.study_skip_counts_mv
TO {database}.study_skip_counts_ch
AS SELECT
    toDate(event_time) AS day,
    user_id,
    pack_version_id,
    topic_id,
    countIf(event_type = 'study_skipped') AS skip_count
FROM {database}.learning_events
GROUP BY day, user_id, pack_version_id, topic_id
"""


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


def insert_event(client: Client, database: str, event: AnalyticsEventMessage) -> None:
    client.insert(
        f"{database}.learning_events",
        [
            [
                ensure_utc(event.event_time),
                event.event_id,
                event.user_id,
                event.session_id,
                event.event_type,
                event.pack_version_id,
                event.pack_title,
                event.topic_id,
                event.phase,
                event.step_id,
                json.dumps(event.payload, ensure_ascii=False),
            ]
        ],
        column_names=[
            "event_time",
            "event_id",
            "user_id",
            "session_id",
            "event_type",
            "pack_version_id",
            "pack_title",
            "topic_id",
            "phase",
            "step_id",
            "payload",
        ],
    )
