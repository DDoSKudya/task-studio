from __future__ import annotations

from datetime import UTC, datetime

import structlog
from app.domain.docker import DockerControl
from app.domain.state import ControllerState
from prometheus_client import Counter

log = structlog.get_logger("orchestrator.controller")

ACTIONS = Counter(
    "orchestrator_actions_total",
    "Orchestrator start/stop actions",
    ["action", "service"],
)


async def ensure_running(
    *,
    docker: DockerControl,
    state: ControllerState,
    service: str,
    reason: str,
) -> None:
    if state.managed_running.get(service, False):
        return
    if not await docker.start_service(service):
        return
    ACTIONS.labels(action="start", service=service).inc()
    state.managed_running[service] = True
    log.info(
        "orchestrator_service_started",
        service=service,
        reason=reason,
        mode=state.mode,
        free_ram_mb=state.free_ram_mb,
    )


async def ensure_stopped(
    *,
    docker: DockerControl,
    state: ControllerState,
    service: str,
    reason: str,
) -> None:
    if not state.managed_running.get(service, False):
        return
    if not await docker.stop_service(service):
        return
    ACTIONS.labels(action="stop", service=service).inc()
    state.managed_running[service] = False
    log.info(
        "orchestrator_service_stopped",
        service=service,
        reason=reason,
        mode=state.mode,
        free_ram_mb=state.free_ram_mb,
    )


def mark_ollama_started(state: ControllerState) -> None:
    state.ollama_last_started = datetime.now(UTC)
