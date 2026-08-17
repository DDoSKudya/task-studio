from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from app.domain.llm.probe.probe_parse import model_is_available
from app.domain.llm.target import LlmTarget

from .registry import AdapterRegistry, load_registry
from .roles import AdapterRole


def registry_path_from_env() -> Path:
    raw = os.getenv("COURSE_ADAPTER_REGISTRY", "").strip()
    return Path(raw) if raw else Path("/data/course-adapters/registry.json")


def load_runtime_registry(path: Path | None = None) -> AdapterRegistry:
    return load_registry(path if path is not None else registry_path_from_env())


def apply_role_adapter(
    target: LlmTarget,
    role: AdapterRole,
    *,
    registry: AdapterRegistry | None = None,
    installed: list[str] | None = None,
) -> LlmTarget:
    book = registry if registry is not None else load_runtime_registry()
    entry = book.shipped(role)
    if entry is None:
        return target
    probe = installed
    if probe is None and target.installed_models is not None:
        probe = list(target.installed_models)
    if probe is None:
        return target
    if not model_is_available(entry.model, probe):
        return target
    if target.model == entry.model:
        return target
    return replace(target, model=entry.model)
