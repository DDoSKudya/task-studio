from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import cast

from studio_contracts.integration_schemas import AdapterCapabilities, AdapterInfo


@dataclass(frozen=True, slots=True)
class AdapterModule:
    info: AdapterInfo
    health: Callable[[], dict[str, object]]
    list_catalog: Callable[..., list[dict[str, object]]]
    import_course: Callable[..., tuple[dict[str, object], dict[str, object]]]
    search_remote: Callable[..., list[dict[str, object]]]


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
        adapter = _load_adapter(entry, manifest_path)
        adapters[adapter.info.id] = adapter
    return adapters


def _load_adapter(module_dir: Path, manifest_path: Path) -> AdapterModule:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        msg = f"invalid integration.json in {module_dir.name}"
        raise ValueError(msg)

    adapter_id = _required_str(manifest, "id")
    entrypoints = manifest.get("entrypoints")
    if not isinstance(entrypoints, dict):
        msg = f"integration.json for {adapter_id} missing entrypoints"
        raise ValueError(msg)

    importer = _import_module(module_dir, "importer")
    capabilities_raw = manifest.get("capabilities")
    capabilities_body = capabilities_raw if isinstance(capabilities_raw, dict) else {}
    info = AdapterInfo(
        id=adapter_id,
        version=_required_str(manifest, "version"),
        display_name=_required_str(manifest, "display_name"),
        capabilities=AdapterCapabilities.model_validate(capabilities_body),
    )
    return AdapterModule(
        info=info,
        health=cast(
            Callable[[], dict[str, object]],
            _resolve_callable(importer, entrypoints, "health"),
        ),
        list_catalog=cast(
            Callable[..., list[dict[str, object]]],
            _resolve_callable(importer, entrypoints, "list_catalog"),
        ),
        import_course=cast(
            Callable[..., tuple[dict[str, object], dict[str, object]]],
            _resolve_callable(importer, entrypoints, "import"),
        ),
        search_remote=cast(
            Callable[..., list[dict[str, object]]],
            _resolve_callable(importer, entrypoints, "search"),
        ),
    )


def _import_module(module_dir: Path, module_name: str) -> ModuleType:
    path = module_dir / f"{module_name}.py"
    if not path.is_file():
        msg = f"missing {module_name}.py in {module_dir.name}"
        raise ValueError(msg)
    spec = importlib.util.spec_from_file_location(f"integration.{module_dir.name}", path)
    if spec is None or spec.loader is None:
        msg = f"cannot load {path}"
        raise ValueError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _resolve_callable(
    module: ModuleType,
    entrypoints: dict[str, object],
    key: str,
) -> Callable[..., object]:
    target = entrypoints.get(key)
    if not isinstance(target, str) or ":" not in target:
        msg = f"missing entrypoint {key!r}"
        raise ValueError(msg)
    symbol_name = target.split(":", 1)[1]
    fn = getattr(module, symbol_name, None)
    if not callable(fn):
        msg = f"entrypoint {target} is not callable"
        raise ValueError(msg)
    return cast(Callable[..., object], fn)


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"integration.json missing {key!r}"
        raise ValueError(msg)
    return value
