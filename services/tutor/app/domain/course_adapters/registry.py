from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .roles import AdapterRole, parse_role


def _finite_float(raw: object) -> float | None:
    if isinstance(raw, bool) or not isinstance(raw, int | float | str):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ShippedAdapter:
    role: AdapterRole
    model: str
    eval_mean: float
    compiler_mean: float
    shipped_at: str


@dataclass(frozen=True, slots=True)
class AdapterRegistry:
    entries: dict[AdapterRole, ShippedAdapter]

    @classmethod
    def empty(cls) -> AdapterRegistry:
        return cls(entries={})

    def shipped(self, role: AdapterRole) -> ShippedAdapter | None:
        return self.entries.get(role)

    def with_entry(self, entry: ShippedAdapter) -> AdapterRegistry:
        updated = dict(self.entries)
        updated[entry.role] = entry
        return AdapterRegistry(entries=updated)

    def to_dict(self) -> dict[str, object]:
        return {
            "adapters": {
                role: {
                    "model": item.model,
                    "eval_mean": item.eval_mean,
                    "compiler_mean": item.compiler_mean,
                    "shipped_at": item.shipped_at,
                }
                for role, item in self.entries.items()
            }
        }


def load_registry(path: Path | None) -> AdapterRegistry:
    if path is None or not path.is_file():
        return AdapterRegistry.empty()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return AdapterRegistry.empty()
    if not isinstance(raw, dict):
        return AdapterRegistry.empty()
    blob = raw.get("adapters")
    if not isinstance(blob, dict):
        return AdapterRegistry.empty()
    entries: dict[AdapterRole, ShippedAdapter] = {}
    for key, item in blob.items():
        role = parse_role(str(key))
        if role is None or not isinstance(item, dict):
            continue
        model = str(item.get("model") or "").strip()
        if not model:
            continue
        eval_mean = _finite_float(item.get("eval_mean"))
        compiler_mean = _finite_float(item.get("compiler_mean"))
        if eval_mean is None or compiler_mean is None:
            continue
        shipped_at = str(item.get("shipped_at") or _utcnow_iso())
        entries[role] = ShippedAdapter(
            role=role,
            model=model,
            eval_mean=eval_mean,
            compiler_mean=compiler_mean,
            shipped_at=shipped_at,
        )
    return AdapterRegistry(entries=entries)


def save_registry(path: Path, registry: AdapterRegistry) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(registry.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def stamp_shipped(
    *,
    role: AdapterRole,
    model: str,
    eval_mean: float,
    compiler_mean: float,
) -> ShippedAdapter:
    return ShippedAdapter(
        role=role,
        model=model,
        eval_mean=eval_mean,
        compiler_mean=compiler_mean,
        shipped_at=_utcnow_iso(),
    )
