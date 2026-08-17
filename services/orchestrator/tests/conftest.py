from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def _import_service_module(service_root: Path, module: str):
    root = str(service_root)
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    return importlib.import_module(module)


@pytest.fixture(scope="session")
def orchestrator_service_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def orchestrator_packages(orchestrator_service_root):
    config = _import_service_module(orchestrator_service_root, "app.config")
    policies = _import_service_module(orchestrator_service_root, "app.domain.policy.policies")
    controller = _import_service_module(orchestrator_service_root, "app.domain.control.controller")
    state = _import_service_module(orchestrator_service_root, "app.domain.control.state")
    metrics = _import_service_module(orchestrator_service_root, "app.domain.telemetry.metrics")
    return config, policies, controller, state, metrics


@pytest.fixture
def orchestrator_modules(orchestrator_packages):
    return orchestrator_packages
