from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

from studio_contracts.api.integration_schemas import AdapterAuthInfo


def parse_auth(auth_raw: object) -> AdapterAuthInfo | None:
    auth_body = auth_raw if isinstance(auth_raw, dict) else None
    if not auth_body:
        return None
    fields_raw = auth_body.get("settings_fields")
    settings_fields = (
        [field for field in fields_raw if isinstance(field, str) and field.strip()]
        if isinstance(fields_raw, list)
        else []
    )
    optional_raw = auth_body.get("optional_settings_fields")
    optional_settings_fields = (
        [field for field in optional_raw if isinstance(field, str) and field.strip()]
        if isinstance(optional_raw, list)
        else []
    )
    auth_type = auth_body.get("type")
    return AdapterAuthInfo(
        type=auth_type if isinstance(auth_type, str) else None,
        settings_fields=settings_fields,
        optional_settings_fields=optional_settings_fields,
    )


def import_module_file(module_dir: Path, module_name: str) -> ModuleType:
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


def resolve_callable(
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


def resolve_optional_callable(
    module: ModuleType,
    entrypoints: dict[str, object],
    key: str,
) -> Callable[..., object] | None:
    target = entrypoints.get(key)
    if target is None or target == "":
        return None
    return resolve_callable(module, entrypoints, key)


def required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"integration.json missing {key!r}"
        raise ValueError(msg)
    return value
