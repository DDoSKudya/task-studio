from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TutorConfig:
    auth_service_url: str
    sessions_service_url: str
    ollama_url: str
    ollama_model: str
    default_provider_url: str
    rate_limit_per_minute: int
    secrets_master_key: str | None


def load_config() -> TutorConfig:
    return TutorConfig(
        auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://auth:8001").rstrip("/"),
        sessions_service_url=os.getenv("SESSIONS_SERVICE_URL", "http://sessions:8003").rstrip("/"),
        ollama_url=os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        default_provider_url=os.getenv("TUTOR_DEFAULT_PROVIDER_URL", "").rstrip("/"),
        rate_limit_per_minute=int(os.getenv("TUTOR_RATE_LIMIT_PER_MINUTE", "30")),
        secrets_master_key=os.getenv("SECRETS_MASTER_KEY"),
    )
