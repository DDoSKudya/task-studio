from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LabRunnerSettings:
    rabbitmq_url: str
    lab_jobs_queue: str
    grading_service_url: str
    dry_run: bool
    default_timeout_seconds: int


def load_settings() -> LabRunnerSettings:
    return LabRunnerSettings(
        rabbitmq_url=os.getenv("RABBITMQ_URL", "").strip(),
        lab_jobs_queue=os.getenv("LAB_JOBS_QUEUE", "lab.jobs"),
        grading_service_url=os.getenv("GRADING_SERVICE_URL", "http://grading:8004").rstrip("/"),
        dry_run=os.getenv("LAB_RUNNER_DRY_RUN", "true").strip().lower() in {"1", "true", "yes"},
        default_timeout_seconds=int(os.getenv("LAB_DEFAULT_TIMEOUT_SECONDS", "120")),
    )
