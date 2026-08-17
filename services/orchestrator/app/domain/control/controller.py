from __future__ import annotations

import httpx
import redis.asyncio as redis
from app.config import OrchestratorSettings
from app.domain.control.controller_apply import apply_balancing
from app.domain.control.controller_modes import (
    apply_maximum,
    apply_power_saving,
    refresh_balancing_signals,
)
from app.domain.control.state import ControllerState
from app.domain.infrastructure.docker import DockerControl
from app.domain.infrastructure.redis_flags import sync_redis_flags
from app.domain.policy.policies import OrchestratorPolicies
from app.domain.telemetry.metrics import HostMetrics, fetch_host_metrics
from prometheus_client import Gauge

FREE_RAM = Gauge("orchestrator_free_ram_mb", "Free RAM reported by node exporter")


class OrchestratorController:
    def __init__(
        self,
        settings: OrchestratorSettings,
        policies: OrchestratorPolicies,
        state: ControllerState,
        docker: DockerControl,
        http_client: httpx.AsyncClient,
        redis_client: redis.Redis | None = None,
    ) -> None:
        self._settings = settings
        self._policies = policies
        self._state = state
        self._docker = docker
        self._http = http_client
        self._redis = redis_client
        self._managed = policies.managed_services

    async def tick(self) -> None:
        self._state.warnings.clear()
        host = await fetch_host_metrics(self._http, self._settings.node_exporter_url)
        self._apply_host_metrics(host)

        if self._state.mode == "balancing":
            await refresh_balancing_signals(
                http=self._http,
                settings=self._settings,
                policies=self._policies,
                state=self._state,
            )

        self._state.managed_running = await self._docker.managed_status(self._managed.all_names())

        match self._state.mode:
            case "maximum":
                await apply_maximum(
                    docker=self._docker,
                    state=self._state,
                    policies=self._policies,
                    host=host,
                )
            case "power_saving":
                await apply_power_saving(
                    docker=self._docker,
                    state=self._state,
                    policies=self._policies,
                )
            case _:
                await apply_balancing(
                    docker=self._docker,
                    state=self._state,
                    policies=self._policies,
                    host=host,
                    lab_runner=self._managed.lab_runner,
                    http=self._http,
                    ollama_url=self._settings.ollama_url,
                )

        await self._sync_redis_flags()

    def _apply_host_metrics(self, host: HostMetrics) -> None:
        self._state.free_ram_mb = host.free_ram_mb
        self._state.load_average = host.load_average
        if host.free_ram_mb is not None:
            FREE_RAM.set(host.free_ram_mb)

    async def _sync_redis_flags(self) -> None:
        if self._redis is None:
            return
        await sync_redis_flags(self._redis, self._state, self._policies)
