from __future__ import annotations

import os
from dataclasses import dataclass
from typing import cast

from studio_contracts.api.orchestrator_schemas import OrchestratorMode

_VALID_MODES = frozenset({"balancing", "maximum", "power_saving"})


@dataclass(frozen=True, slots=True)
class OrchestratorSettings:
    mode: OrchestratorMode
    policies_path: str
    compose_project: str
    docker_socket: str
    prometheus_url: str
    node_exporter_url: str
    pyroscope_url: str
    auth_service_url: str
    redis_url: str
    system_token: str
    tutor_default_provider_url: str
    ollama_url: str


def load_settings() -> OrchestratorSettings:
    return OrchestratorSettings(
        mode=_parse_mode(os.getenv("ORCHESTRATOR_MODE", "balancing")),
        policies_path=os.getenv(
            "ORCHESTRATOR_POLICIES_PATH",
            "/etc/task-studio/policies.yaml",
        ),
        compose_project=os.getenv("COMPOSE_PROJECT_NAME", "task-studio"),
        docker_socket=os.getenv("DOCKER_SOCKET", "/var/run/docker.sock"),
        prometheus_url=os.getenv("PROMETHEUS_URL", "http://prometheus:9090").rstrip("/"),
        node_exporter_url=os.getenv("NODE_EXPORTER_URL", "http://node-exporter:9100").rstrip("/"),
        pyroscope_url=os.getenv("PYROSCOPE_URL", "http://pyroscope:4040").rstrip("/"),
        auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://auth:8001").rstrip("/"),
        redis_url=os.getenv("REDIS_URL", "").strip(),
        system_token=os.getenv("ORCHESTRATOR_SYSTEM_TOKEN", "").strip(),
        tutor_default_provider_url=os.getenv("TUTOR_DEFAULT_PROVIDER_URL", "").strip(),
        ollama_url=os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/"),
    )


def _parse_mode(raw: str) -> OrchestratorMode:
    normalized = raw.strip().lower()
    if normalized in _VALID_MODES:
        return cast(OrchestratorMode, normalized)
    return "balancing"
