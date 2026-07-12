from __future__ import annotations

import asyncio

import httpx
import redis.asyncio as redis
import structlog

from app.config import OrchestratorSettings
from app.domain.controller import OrchestratorController
from app.domain.docker import DockerControl
from app.domain.policies import OrchestratorPolicies
from app.domain.state import ControllerState

log = structlog.get_logger("orchestrator.worker")


def start_control_loop(
    settings: OrchestratorSettings,
    policies: OrchestratorPolicies,
    state: ControllerState,
    docker: DockerControl,
    http_client: httpx.AsyncClient,
    *,
    redis_client: redis.Redis | None = None,
) -> asyncio.Task[None]:
    controller = OrchestratorController(
        settings,
        policies,
        state,
        docker,
        http_client,
        redis_client,
    )

    async def _runner() -> None:
        interval = policies.loop_interval_seconds
        while True:
            try:
                await controller.tick()
            except Exception:
                log.exception("orchestrator_tick_failed")
            await asyncio.sleep(interval)

    return asyncio.create_task(_runner())
