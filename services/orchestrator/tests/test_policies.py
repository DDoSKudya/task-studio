from __future__ import annotations

from pathlib import Path


def test_load_policies_reads_managed_services(orchestrator_modules) -> None:
    _config, policies_mod, _controller_mod, _state_mod, _metrics_mod = orchestrator_modules
    path = Path(__file__).resolve().parents[3] / "deploy/orchestrator/policies.yaml"
    policies = policies_mod.load_policies(path)
    assert policies.managed_services.ollama == "ollama"
    assert policies.balancing.ollama.idle_stop_minutes == 30
    assert "lsp-pyright" in policies.managed_services.lsp
