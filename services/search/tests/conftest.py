from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

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
def build_app(monkeypatch: pytest.MonkeyPatch):
    service_root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("RABBITMQ_URL", "")
    monkeypatch.setenv("MEILISEARCH_URL", "http://meili.test:7700")
    main_module = _import_service_main(service_root)
    monkeypatch.setattr(main_module, "ensure_index", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_module, "meili_client", lambda _settings: MagicMock())
    return main_module.build_app
