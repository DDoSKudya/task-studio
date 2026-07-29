from __future__ import annotations

from app.domain.controller_actions import ensure_running, ensure_stopped, mark_ollama_started
from app.domain.docker import DockerControl
from app.domain.llm_signals import ollama_stop_reason
from app.domain.metrics import HostMetrics
from app.domain.policies import OrchestratorPolicies
from app.domain.state import ControllerState


async def balance_ollama(
    *,
    docker: DockerControl,
    state: ControllerState,
    policies: OrchestratorPolicies,
    host: HostMetrics,
    all_external: bool,
) -> None:
    policy = policies.balancing.ollama
    service = policies.managed_services.ollama
    running = state.managed_running.get(service, False)
    low_ram = host.free_ram_mb is not None and host.free_ram_mb < policy.min_free_ram_mb

    if all_external or low_ram or state.grading_cpu_hot:
        if running:
            await ensure_stopped(
                docker=docker,
                state=state,
                service=service,
                reason=ollama_stop_reason(
                    low_ram=low_ram,
                    grading_cpu_hot=bool(state.grading_cpu_hot),
                ),
            )
        return

    if not running:
        await ensure_running(
            docker=docker,
            state=state,
            service=service,
            reason="local_llm_needed",
        )
        mark_ollama_started(state)
        return

    idle_minutes = state.minutes_since(state.ollama_last_started)
    if idle_minutes is not None and idle_minutes >= policy.idle_stop_minutes:
        await ensure_stopped(docker=docker, state=state, service=service, reason="idle_timeout")


async def balance_lsp(
    *,
    docker: DockerControl,
    state: ControllerState,
    policies: OrchestratorPolicies,
) -> None:
    policy = policies.balancing.lsp
    if state.editor_open:
        for service in policies.managed_services.lsp:
            await ensure_running(docker=docker, state=state, service=service, reason="editor_open")
        return

    idle_minutes = state.minutes_since(state.editor_last_activity)
    if idle_minutes is None or idle_minutes < policy.idle_stop_minutes:
        return
    for service in policies.managed_services.lsp:
        if state.managed_running.get(service, False):
            await ensure_stopped(docker=docker, state=state, service=service, reason="lsp_idle")
