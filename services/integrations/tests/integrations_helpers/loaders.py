from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType


def load_integrations_module(module_name: str) -> ModuleType:
    service_root = Path(__file__).resolve().parents[2]
    root = str(service_root)
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    return importlib.import_module(module_name)
