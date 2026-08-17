from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

from studio_contracts.api.integration_schemas import AdapterCapabilities, AdapterInfo

from .adapter_load_helpers import (
    import_module_file,
    parse_auth,
    required_str,
    resolve_callable,
    resolve_optional_callable,
)
from .registry_types import AdapterModule

__all__ = [
    "load_adapter",
    "parse_auth",
    "import_module_file",
    "resolve_callable",
    "required_str",
]


def load_adapter(module_dir: Path, manifest_path: Path) -> AdapterModule:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        msg = f"invalid integration.json in {module_dir.name}"
        raise ValueError(msg)

    adapter_id = required_str(manifest, "id")
    entrypoints = manifest.get("entrypoints")
    if not isinstance(entrypoints, dict):
        msg = f"integration.json for {adapter_id} missing entrypoints"
        raise ValueError(msg)

    importer = import_module_file(module_dir, "importer")
    capabilities_raw = manifest.get("capabilities")
    capabilities_body = capabilities_raw if isinstance(capabilities_raw, dict) else {}
    auth = parse_auth(manifest.get("auth"))
    info = AdapterInfo(
        id=adapter_id,
        version=required_str(manifest, "version"),
        display_name=required_str(manifest, "display_name"),
        capabilities=AdapterCapabilities.model_validate(capabilities_body),
        auth=auth,
    )
    enroll_fn = resolve_optional_callable(importer, entrypoints, "enroll")
    return AdapterModule(
        info=info,
        health=cast(
            Callable[[], dict[str, object]],
            resolve_callable(importer, entrypoints, "health"),
        ),
        list_catalog=cast(
            Callable[..., list[dict[str, object]]],
            resolve_callable(importer, entrypoints, "list_catalog"),
        ),
        import_course=cast(
            Callable[..., tuple[dict[str, object], dict[str, object]]],
            resolve_callable(importer, entrypoints, "import"),
        ),
        search_remote=cast(
            Callable[..., list[dict[str, object]]],
            resolve_callable(importer, entrypoints, "search"),
        ),
        enroll=cast(Callable[..., dict[str, object]], enroll_fn) if enroll_fn else None,
    )
