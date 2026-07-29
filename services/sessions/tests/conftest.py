from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def _prefer_root(service_root: Path) -> None:
    root = str(service_root)
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)


def import_sessions_module(module: str) -> ModuleType:
    service_root = Path(__file__).resolve().parents[1]
    _prefer_root(service_root)
    _purge_app_modules()
    return importlib.import_module(module)


def _import_service_main(service_root: Path):
    _prefer_root(service_root)
    _purge_app_modules()
    return importlib.import_module("app.main")


@pytest.fixture
def build_app():
    service_root = Path(__file__).resolve().parents[1]
    return _import_service_main(service_root).build_app


@pytest.fixture
def sessions_domain() -> ModuleType:
    return import_sessions_module("app.domain.sessions")
