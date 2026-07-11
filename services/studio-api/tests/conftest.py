from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def _import_service_main(service_root: Path):
    root = str(service_root)
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    return importlib.import_module("app.main")


@pytest.fixture
def build_app():
    service_root = Path(__file__).resolve().parents[1]
    return _import_service_main(service_root).build_app
