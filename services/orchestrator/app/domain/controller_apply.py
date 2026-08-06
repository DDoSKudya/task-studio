from __future__ import annotations

import httpx
from app.domain.controller_actions import ensure_running
from app.domain.controller_balance import balance_lsp, balance_ollama
from app.domain.docker import DockerControl
from app.domain.metrics import HostMetrics
from app.domain.policies import OrchestratorPolicies
from app.domain.state import ControllerState


async def apply_balancing(
    *,
    docker: DockerControl,
    state: ControllerState,
    policies: OrchestratorPolicies,
    host: HostMetrics,
    lab_runner: str,
    http: httpx.AsyncClient,
    ollama_url: str,
) -> None:
    all_external = state.all_users_external_llm or False
    await balance_ollama(
        docker=docker,
        state=state,
        policies=policies,
        host=host,
        all_external=all_external,
        http=http,
        ollama_url=ollama_url,
    )
    await balance_lsp(
        docker=docker,
        state=state,
        policies=policies,
    )
    await ensure_running(
        docker=docker,
        state=state,
        service=lab_runner,
        reason="lab_available",
    )
