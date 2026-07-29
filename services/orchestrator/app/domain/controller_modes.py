from __future__ import annotations

import asyncio

import httpx
import structlog
from app.config import OrchestratorSettings
from app.domain.controller_actions import ensure_running, ensure_stopped
from app.domain.llm_signals import all_users_external
from app.domain.metrics import HostMetrics
from app.domain.policies import OrchestratorPolicies
from app.domain.state import ControllerState

log = structlog.get_logger("orchestrator.controller")


async def refresh_balancing_signals(
    *,
    http: httpx.AsyncClient,
    settings: OrchestratorSettings,
    policies: OrchestratorPolicies,
    state: ControllerState,
) -> None:
    from app.domain import metrics as metrics_mod

    summary = await metrics_mod.fetch_tutor_llm_summary(
        http,
        settings.auth_service_url,
        system_token=settings.system_token,
    )
    state.all_users_external_llm = all_users_external(settings, summary)
    state.grading_cpu_hot = await metrics_mod.grading_cpu_hot(
        http,
        settings.prometheus_url,
        threshold=policies.balancing.grading_cpu_defer_ollama,
        pyroscope_url=settings.pyroscope_url,
    )


async def apply_maximum(
    *,
    docker,
    state: ControllerState,
    policies: OrchestratorPolicies,
    host: HostMetrics,
) -> None:
    await asyncio.gather(
        *(
            ensure_running(
                docker=docker,
                state=state,
                service=service,
                reason="maximum_mode",
            )
            for service in policies.managed_services.all_names()
        )
    )

    warning_mb = policies.maximum.min_free_ram_warning_mb
    if host.free_ram_mb is not None and host.free_ram_mb < warning_mb:
        state.warnings.append(f"free RAM below {warning_mb} MB in maximum mode")
        log.warning("orchestrator_maximum_ram_warning", free_ram_mb=host.free_ram_mb)


async def apply_power_saving(
    *,
    docker,
    state: ControllerState,
    policies: OrchestratorPolicies,
) -> None:
    await asyncio.gather(
        *(
            ensure_stopped(
                docker=docker,
                state=state,
                service=service,
                reason="power_saving",
            )
            for service in policies.managed_services.all_names()
        )
    )
