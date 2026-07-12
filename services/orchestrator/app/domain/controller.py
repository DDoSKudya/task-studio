from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
import redis.asyncio as redis
import structlog
from app.config import OrchestratorSettings
from app.domain.docker import DockerControl
from app.domain.metrics import (
    HostMetrics,
    fetch_host_metrics,
    fetch_tutor_llm_summary,
    grading_cpu_hot,
)
from app.domain.policies import OrchestratorPolicies
from app.domain.state import ControllerState
from prometheus_client import Counter, Gauge
from studio_common.orchestrator_flags import (
    ANALYTICS_BATCH_SLEEP_KEY,
    PAUSE_IMPORT_KEY,
    PAUSE_SEARCH_INDEX_KEY,
)
from studio_contracts.orchestrator_schemas import TutorLlmSummaryResponse

log = structlog.get_logger("orchestrator.controller")

ACTIONS = Counter(
    "orchestrator_actions_total",
    "Orchestrator start/stop actions",
    ["action", "service"],
)
FREE_RAM = Gauge("orchestrator_free_ram_mb", "Free RAM reported by node exporter")
_REDIS_FLAG_TTL_SECONDS = 120


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
            await self._refresh_balancing_signals()

        self._state.managed_running = await self._docker.managed_status(self._managed.all_names())

        match self._state.mode:
            case "maximum":
                await self._apply_maximum(host)
            case "power_saving":
                await self._apply_power_saving()
            case _:
                await self._apply_balancing(host)

        await self._sync_redis_flags()

    def _apply_host_metrics(self, host: HostMetrics) -> None:
        self._state.free_ram_mb = host.free_ram_mb
        self._state.load_average = host.load_average
        if host.free_ram_mb is not None:
            FREE_RAM.set(host.free_ram_mb)

    async def _refresh_balancing_signals(self) -> None:
        summary = await fetch_tutor_llm_summary(
            self._http,
            self._settings.auth_service_url,
            system_token=self._settings.system_token,
        )
        self._state.all_users_external_llm = self._all_users_external(summary)
        self._state.grading_cpu_hot = await grading_cpu_hot(
            self._http,
            self._settings.prometheus_url,
            threshold=self._policies.balancing.grading_cpu_defer_ollama,
            pyroscope_url=self._settings.pyroscope_url,
        )

    async def _apply_maximum(self, host: HostMetrics) -> None:
        await asyncio.gather(
            *(
                self._ensure_running(service, reason="maximum_mode")
                for service in self._managed.all_names()
            )
        )

        warning_mb = self._policies.maximum.min_free_ram_warning_mb
        if host.free_ram_mb is not None and host.free_ram_mb < warning_mb:
            self._state.warnings.append(f"free RAM below {warning_mb} MB in maximum mode")
            log.warning("orchestrator_maximum_ram_warning", free_ram_mb=host.free_ram_mb)

    async def _apply_power_saving(self) -> None:
        await asyncio.gather(
            *(
                self._ensure_stopped(service, reason="power_saving")
                for service in self._managed.all_names()
            )
        )

    async def _apply_balancing(self, host: HostMetrics) -> None:
        all_external = self._state.all_users_external_llm or False
        await self._balance_ollama(host, all_external=all_external)
        await self._balance_lsp()
        await self._ensure_running(self._managed.lab_runner, reason="lab_available")

    async def _balance_ollama(self, host: HostMetrics, *, all_external: bool) -> None:
        policy = self._policies.balancing.ollama
        service = self._managed.ollama
        running = self._state.managed_running.get(service, False)
        low_ram = host.free_ram_mb is not None and host.free_ram_mb < policy.min_free_ram_mb

        if all_external or low_ram or self._state.grading_cpu_hot:
            if running:
                await self._ensure_stopped(
                    service,
                    reason=self._ollama_stop_reason(low_ram=low_ram),
                )
            return

        if not running:
            await self._ensure_running(service, reason="local_llm_needed")
            self._state.ollama_last_started = datetime.now(UTC)
            return

        idle_minutes = self._state.minutes_since(self._state.ollama_last_started)
        if idle_minutes is not None and idle_minutes >= policy.idle_stop_minutes:
            await self._ensure_stopped(service, reason="idle_timeout")

    async def _balance_lsp(self) -> None:
        policy = self._policies.balancing.lsp
        if self._state.editor_open:
            for service in self._managed.lsp:
                await self._ensure_running(service, reason="editor_open")
            return

        idle_minutes = self._state.minutes_since(self._state.editor_last_activity)
        if idle_minutes is None or idle_minutes < policy.idle_stop_minutes:
            return
        for service in self._managed.lsp:
            if self._state.managed_running.get(service, False):
                await self._ensure_stopped(service, reason="lsp_idle")

    async def _ensure_running(self, service: str, *, reason: str) -> None:
        if self._state.managed_running.get(service, False):
            return
        if not await self._docker.start_service(service):
            return
        ACTIONS.labels(action="start", service=service).inc()
        self._state.managed_running[service] = True
        log.info(
            "orchestrator_service_started",
            service=service,
            reason=reason,
            mode=self._state.mode,
            free_ram_mb=self._state.free_ram_mb,
        )

    async def _ensure_stopped(self, service: str, *, reason: str) -> None:
        if not self._state.managed_running.get(service, False):
            return
        if not await self._docker.stop_service(service):
            return
        ACTIONS.labels(action="stop", service=service).inc()
        self._state.managed_running[service] = False
        log.info(
            "orchestrator_service_stopped",
            service=service,
            reason=reason,
            mode=self._state.mode,
            free_ram_mb=self._state.free_ram_mb,
        )

    async def _sync_redis_flags(self) -> None:
        if self._redis is None:
            return

        pause_search, pause_import, analytics_sleep = self._pause_directives()

        if pause_search:
            await self._redis.set(PAUSE_SEARCH_INDEX_KEY, "1", ex=_REDIS_FLAG_TTL_SECONDS)
        else:
            await self._redis.delete(PAUSE_SEARCH_INDEX_KEY)

        if pause_import:
            await self._redis.set(PAUSE_IMPORT_KEY, "1", ex=_REDIS_FLAG_TTL_SECONDS)
        else:
            await self._redis.delete(PAUSE_IMPORT_KEY)

        if analytics_sleep > 0:
            await self._redis.set(
                ANALYTICS_BATCH_SLEEP_KEY,
                str(analytics_sleep),
                ex=_REDIS_FLAG_TTL_SECONDS,
            )
        else:
            await self._redis.delete(ANALYTICS_BATCH_SLEEP_KEY)

    def _pause_directives(self) -> tuple[bool, bool, int]:
        if self._state.mode == "power_saving":
            policy = self._policies.power_saving
            return (
                True,
                not policy.allow_background_import,
                policy.analytics_batch_sleep_seconds,
            )

        if self._state.mode == "balancing":
            free_ram = self._state.free_ram_mb
            threshold = self._policies.balancing.meilisearch_pause_below_ram_mb
            if free_ram is not None and free_ram < threshold:
                return True, False, 0

        return False, False, 0

    def _ollama_stop_reason(self, *, low_ram: bool) -> str:
        if low_ram:
            return "low_ram"
        if self._state.grading_cpu_hot:
            return "grading_cpu_hot"
        return "all_users_external_llm"

    def _all_users_external(self, summary: TutorLlmSummaryResponse | None) -> bool:
        if self._settings.tutor_default_provider_url:
            return True
        if summary is None:
            return False
        if summary.user_count == 0:
            return True
        return summary.all_external
