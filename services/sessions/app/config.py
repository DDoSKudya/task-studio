from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionsSettings:
    catalog_service_url: str
    grading_service_url: str
    analytics_service_url: str
    rabbitmq_url: str
    analytics_events_queue: str


def load_settings() -> SessionsSettings:
    return SessionsSettings(
        catalog_service_url=os.getenv("CATALOG_SERVICE_URL", "http://catalog:8002").rstrip("/"),
        grading_service_url=os.getenv("GRADING_SERVICE_URL", "http://grading:8004").rstrip("/"),
        analytics_service_url=os.getenv("ANALYTICS_SERVICE_URL", "http://analytics:8008").rstrip(
            "/"
        ),
        rabbitmq_url=os.getenv("RABBITMQ_URL", "").strip(),
        analytics_events_queue=os.getenv("ANALYTICS_EVENTS_QUEUE", "analytics.events"),
    )
