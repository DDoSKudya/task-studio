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
    auth_service_url: str
    tutor_service_url: str
    media_service_url: str
    packs_root: str
    llm_grade_enabled: bool
    llm_grade_min_confidence: float
    secrets_master_key: str | None


def load_settings() -> GradingSettings:
    master = os.getenv("SECRETS_MASTER_KEY", "").strip()
    return GradingSettings(
        piston_url=os.getenv("PISTON_URL", "http://piston:2000").rstrip("/"),
        piston_timeout_seconds=float(os.getenv("PISTON_TIMEOUT_SECONDS", "10")),
        rabbitmq_url=os.getenv("RABBITMQ_URL", "").strip(),
        grading_jobs_queue=os.getenv("GRADING_JOBS_QUEUE", "grading.jobs"),
        lab_jobs_queue=os.getenv("LAB_JOBS_QUEUE", "lab.jobs"),
        catalog_service_url=os.getenv("CATALOG_SERVICE_URL", "http://catalog:8002").rstrip("/"),
        sessions_service_url=os.getenv("SESSIONS_SERVICE_URL", "http://sessions:8003").rstrip("/"),
        auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://auth:8001").rstrip("/"),
        tutor_service_url=os.getenv("TUTOR_SERVICE_URL", "http://tutor:8006").rstrip("/"),
        media_service_url=os.getenv("MEDIA_SERVICE_URL", "http://media:8009").rstrip("/"),
        packs_root=os.getenv("PACKS_ROOT", "/data/packs"),
        llm_grade_enabled=os.getenv("LLM_GRADE_ENABLED", "true").strip().lower()
        in {"1", "true", "yes", "on"},
        llm_grade_min_confidence=float(os.getenv("LLM_GRADE_MIN_CONFIDENCE", "0.65")),
        secrets_master_key=master or None,
    )
