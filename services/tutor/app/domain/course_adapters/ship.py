from __future__ import annotations

from pathlib import Path

from .evaluate import EvalReport, assert_adapter_ships
from .registry import AdapterRegistry, load_registry, save_registry, stamp_shipped
from .roles import AdapterRole, ollama_model_for_role


def ship_adapter(
    *,
    role: AdapterRole,
    adapter: EvalReport,
    compiler: EvalReport,
    registry_path: Path,
    model: str | None = None,
    registry: AdapterRegistry | None = None,
) -> AdapterRegistry:
    assert_adapter_ships(role=role, adapter=adapter, compiler=compiler)
    entry = stamp_shipped(
        role=role,
        model=model or ollama_model_for_role(role),
        eval_mean=adapter.mean,
        compiler_mean=compiler.mean,
    )
    book = (registry if registry is not None else load_registry(registry_path)).with_entry(entry)
    save_registry(registry_path, book)
    return book
