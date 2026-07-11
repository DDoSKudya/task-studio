from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionsSettings:
    catalog_service_url: str
    grading_service_url: str


def load_settings() -> SessionsSettings:
    return SessionsSettings(
        catalog_service_url=os.getenv("CATALOG_SERVICE_URL", "http://catalog:8002").rstrip("/"),
        grading_service_url=os.getenv("GRADING_SERVICE_URL", "http://grading:8004").rstrip("/"),
    )
