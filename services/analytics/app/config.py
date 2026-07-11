from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalyticsSettings:
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_database: str
    rabbitmq_url: str
    analytics_events_queue: str


def load_settings() -> AnalyticsSettings:
    return AnalyticsSettings(
        clickhouse_host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
        clickhouse_port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        clickhouse_user=os.getenv("CLICKHOUSE_USER", "default"),
        clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        clickhouse_database=os.getenv("CLICKHOUSE_DATABASE", "analytics"),
        rabbitmq_url=os.getenv("RABBITMQ_URL", "").strip(),
        analytics_events_queue=os.getenv("ANALYTICS_EVENTS_QUEUE", "analytics.events"),
    )
