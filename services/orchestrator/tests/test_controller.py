from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from studio_contracts.orchestrator_schemas import OrchestratorMode, TutorLlmSummaryResponse


def _settings(config, *, mode: OrchestratorMode = "balancing"):
    return config.OrchestratorSettings(
        mode=mode,
        policies_path="/etc/policies.yaml",
        compose_project="task-studio",
        docker_socket="/var/run/docker.sock",
        prometheus_url="http://prometheus:9090",
        node_exporter_url="http://node-exporter:9100",
        pyroscope_url="http://pyroscope:4040",
        auth_service_url="http://auth:8001",
        redis_url="",
        system_token="",
        tutor_default_provider_url="",
    )


def _policies(policies_mod):
    return policies_mod.OrchestratorPolicies(
        balancing=policies_mod.BalancingPolicy(
            ollama=policies_mod.OllamaPolicy(idle_stop_minutes=30, min_free_ram_mb=1536),
            lsp=policies_mod.LspPolicy(idle_stop_minutes=15),
            meilisearch_pause_below_ram_mb=1536,
            grading_cpu_defer_ollama=0.5,
        ),
        maximum=policies_mod.MaximumPolicy(min_free_ram_warning_mb=1638),
        power_saving=policies_mod.PowerSavingPolicy(
            allow_background_import=False,
            analytics_batch_sleep_seconds=60,
        ),
        loop_interval_seconds=30,
        managed_services=policies_mod.ManagedServices(
            ollama="ollama",
            lab_runner="lab-runner",
            lsp=("lsp-pyright", "lsp-typescript"),
        ),
    )


def _controller(
    orchestrator_modules,
    *,
    mode: OrchestratorMode = "balancing",
    docker: AsyncMock | None = None,
):
    config, policies_mod, controller_mod, state_mod, metrics_mod = orchestrator_modules
    state = state_mod.ControllerState(mode=mode)
    if docker is None:
        docker_mock = AsyncMock()
        docker_mock.managed_status = AsyncMock(
            return_value={
                "ollama": True,
                "lab-runner": True,
                "lsp-pyright": True,
                "lsp-typescript": False,
            }
        )
    else:
        docker_mock = docker
    docker_mock.stop_service = AsyncMock(return_value=True)
    docker_mock.start_service = AsyncMock(return_value=True)
    http = AsyncMock()
    controller = controller_mod.OrchestratorController(
        _settings(config, mode=mode),
        _policies(policies_mod),
        state,
        docker_mock,
        http,
    )
    host = metrics_mod.HostMetrics(free_ram_mb=4096, load_average=0.2)
    return controller, state, docker_mock, controller_mod, host


@pytest.mark.asyncio
async def test_balancing_stops_ollama_when_all_users_external(
    orchestrator_modules,
    monkeypatch,
) -> None:
    controller, _state, docker, controller_mod, host = _controller(orchestrator_modules)
    monkeypatch.setattr(controller_mod, "fetch_host_metrics", AsyncMock(return_value=host))
    monkeypatch.setattr(
        controller_mod,
        "fetch_tutor_llm_summary",
        AsyncMock(
            return_value=TutorLlmSummaryResponse(
                user_count=2,
                local_fallback_users=0,
                all_external=True,
            )
        ),
    )
    monkeypatch.setattr(controller_mod, "grading_cpu_hot", AsyncMock(return_value=False))

    await controller.tick()

    docker.stop_service.assert_any_call("ollama")


@pytest.mark.asyncio
async def test_power_saving_stops_lab_and_lsp(orchestrator_modules, monkeypatch) -> None:
    controller, _state, docker, controller_mod, host = _controller(
        orchestrator_modules,
        mode="power_saving",
    )
    monkeypatch.setattr(controller_mod, "fetch_host_metrics", AsyncMock(return_value=host))
    monkeypatch.setattr(controller_mod, "fetch_tutor_llm_summary", AsyncMock(return_value=None))
    monkeypatch.setattr(controller_mod, "grading_cpu_hot", AsyncMock(return_value=False))

    await controller.tick()

    docker.stop_service.assert_any_call("lab-runner")
    docker.stop_service.assert_any_call("lsp-pyright")


@pytest.mark.asyncio
async def test_maximum_keeps_services_running(orchestrator_modules, monkeypatch) -> None:
    docker = AsyncMock()
    docker.managed_status = AsyncMock(
        return_value={
            "ollama": False,
            "lab-runner": False,
            "lsp-pyright": False,
            "lsp-typescript": False,
        }
    )
    docker.start_service = AsyncMock(return_value=True)
    docker.stop_service = AsyncMock(return_value=True)
    controller, _state, docker, controller_mod, host = _controller(
        orchestrator_modules,
        mode="maximum",
        docker=docker,
    )
    monkeypatch.setattr(controller_mod, "fetch_host_metrics", AsyncMock(return_value=host))
    monkeypatch.setattr(controller_mod, "fetch_tutor_llm_summary", AsyncMock(return_value=None))
    monkeypatch.setattr(controller_mod, "grading_cpu_hot", AsyncMock(return_value=False))

    await controller.tick()

    docker.start_service.assert_any_call("ollama")
    docker.stop_service.assert_not_called()


@pytest.mark.asyncio
async def test_balancing_stops_idle_lsp(orchestrator_modules, monkeypatch) -> None:
    controller, state, docker, controller_mod, host = _controller(orchestrator_modules)
    state.editor_open = False
    state.editor_last_activity = datetime.now(UTC) - timedelta(minutes=20)
    monkeypatch.setattr(controller_mod, "fetch_host_metrics", AsyncMock(return_value=host))
    monkeypatch.setattr(
        controller_mod,
        "fetch_tutor_llm_summary",
        AsyncMock(
            return_value=TutorLlmSummaryResponse(
                user_count=1,
                local_fallback_users=1,
                all_external=False,
            )
        ),
    )
    monkeypatch.setattr(controller_mod, "grading_cpu_hot", AsyncMock(return_value=False))

    await controller.tick()

    docker.stop_service.assert_any_call("lsp-pyright")
