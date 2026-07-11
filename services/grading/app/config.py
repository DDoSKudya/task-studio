from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GradingSettings:
    piston_url: str
    piston_timeout_seconds: float
    rabbitmq_url: str
    grading_jobs_queue: str
    lab_jobs_queue: str
    catalog_service_url: str
    sessions_service_url: str


def load_settings() -> GradingSettings:
    return GradingSettings(
        piston_url=os.getenv("PISTON_URL", "http://piston:2000").rstrip("/"),
        piston_timeout_seconds=float(os.getenv("PISTON_TIMEOUT_SECONDS", "10")),
        rabbitmq_url=os.getenv("RABBITMQ_URL", "").strip(),
        grading_jobs_queue=os.getenv("GRADING_JOBS_QUEUE", "grading.jobs"),
        lab_jobs_queue=os.getenv("LAB_JOBS_QUEUE", "lab.jobs"),
        catalog_service_url=os.getenv("CATALOG_SERVICE_URL", "http://catalog:8002").rstrip("/"),
        sessions_service_url=os.getenv("SESSIONS_SERVICE_URL", "http://sessions:8003").rstrip("/"),
    )
