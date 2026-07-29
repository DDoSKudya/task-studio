from __future__ import annotations

from pathlib import Path

from .adapter_load import load_adapter
from .registry_types import AdapterModule

__all__ = [
    "AdapterModule",
    "discover_adapters",
]


def discover_adapters(modules_root: Path) -> dict[str, AdapterModule]:
    adapters: dict[str, AdapterModule] = {}
    if not modules_root.is_dir():
        return adapters

    for entry in sorted(modules_root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_"):
            continue
        manifest_path = entry / "integration.json"
        if not manifest_path.is_file():
            continue
        adapter = load_adapter(entry, manifest_path)
        adapters[adapter.info.id] = adapter
    return adapters
