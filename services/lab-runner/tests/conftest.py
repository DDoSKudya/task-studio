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


@pytest.fixture
def lab_runner_modules():
    service_root = Path(__file__).resolve().parents[1]
    config = _import_service_module(service_root, "app.config")
    runner = _import_service_module(service_root, "app.domain.runner")
    return config, runner
