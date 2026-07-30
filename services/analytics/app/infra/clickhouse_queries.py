from __future__ import annotations

import json

from app.datetime_utils import ensure_utc
from clickhouse_connect.driver.client import Client
from studio_contracts.analytics_schemas import AnalyticsEventMessage


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


def fetch_daily_progress(
    client: Client,
    database: str,
    *,
    user_id: object,
    since_day: object,
) -> list[tuple[object, int, int]]:

    result = client.query(
        f"""
        SELECT
            day,
            sum(sessions_started) AS sessions_started,
            sum(steps_completed) AS steps_completed
        FROM {database}.daily_user_progress_ch
        WHERE user_id = {{uid:UUID}} AND day >= {{since:Date}}
        GROUP BY day
        ORDER BY day ASC
        """,
        parameters={"uid": str(user_id), "since": str(since_day)},
    )
    rows: list[tuple[object, int, int]] = []
    for day, sessions, steps in result.result_rows:
        rows.append((day, int(sessions or 0), int(steps or 0)))
    return rows
