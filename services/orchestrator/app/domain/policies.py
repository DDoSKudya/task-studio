from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True, slots=True)
class OllamaPolicy:
    idle_stop_minutes: int
    min_free_ram_mb: int


@dataclass(frozen=True, slots=True)
class LspPolicy:
    idle_stop_minutes: int


@dataclass(frozen=True, slots=True)
class BalancingPolicy:
    ollama: OllamaPolicy
    lsp: LspPolicy
    meilisearch_pause_below_ram_mb: int
    grading_cpu_defer_ollama: float


@dataclass(frozen=True, slots=True)
class MaximumPolicy:
    min_free_ram_warning_mb: int


@dataclass(frozen=True, slots=True)
class PowerSavingPolicy:
    allow_background_import: bool
    analytics_batch_sleep_seconds: int


@dataclass(frozen=True, slots=True)
class ManagedServices:
    ollama: str
    lab_runner: str
    lsp: tuple[str, ...]

    def all_names(self) -> tuple[str, ...]:
        return (self.ollama, self.lab_runner, *self.lsp)


@dataclass(frozen=True, slots=True)
class OrchestratorPolicies:
    balancing: BalancingPolicy
    maximum: MaximumPolicy
    power_saving: PowerSavingPolicy
    loop_interval_seconds: int
    managed_services: ManagedServices


def load_policies(path: str | Path) -> OrchestratorPolicies:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = "policies file must be a mapping"
        raise ValueError(msg)

    balancing = _require_mapping(raw, "balancing")
    maximum = _require_mapping(raw, "maximum")
    power_saving = _require_mapping(raw, "power_saving")
    managed = _require_mapping(raw, "managed_services")
    lsp_services = managed.get("lsp")
    if not isinstance(lsp_services, list) or not lsp_services:
        msg = "managed_services.lsp must be a non-empty list"
        raise ValueError(msg)

    meili = _require_mapping(balancing, "meilisearch")
    ollama = _require_mapping(balancing, "ollama")
    return OrchestratorPolicies(
        balancing=BalancingPolicy(
            ollama=OllamaPolicy(
                idle_stop_minutes=_positive_int(
                    ollama,
                    "idle_stop_minutes",
                    default=30,
                ),
                min_free_ram_mb=_positive_int(
                    ollama,
                    "min_free_ram_mb",
                    default=1536,
                ),
            ),
            lsp=LspPolicy(
                idle_stop_minutes=_positive_int(
                    _require_mapping(balancing, "lsp"),
                    "idle_stop_minutes",
                    default=15,
                ),
            ),
            meilisearch_pause_below_ram_mb=_positive_int(
                meili,
                "pause_indexing_below_ram_mb",
                default=1536,
            ),
            grading_cpu_defer_ollama=_positive_float(
                balancing,
                "grading_cpu_defer_ollama",
                default=0.5,
            ),
        ),
        maximum=MaximumPolicy(
            min_free_ram_warning_mb=_positive_int(
                maximum,
                "min_free_ram_warning_mb",
                default=1638,
            ),
        ),
        power_saving=PowerSavingPolicy(
            allow_background_import=bool(power_saving.get("allow_background_import", False)),
            analytics_batch_sleep_seconds=_positive_int(
                power_saving,
                "analytics_batch_sleep_seconds",
                default=60,
            ),
        ),
        loop_interval_seconds=_positive_int(raw, "loop_interval_seconds", default=30),
        managed_services=ManagedServices(
            ollama=str(managed.get("ollama", "ollama")),
            lab_runner=str(managed.get("lab_runner", "lab-runner")),
            lsp=tuple(str(name) for name in lsp_services),
        ),
    )


def _require_mapping(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key)
    if not isinstance(value, dict):
        msg = f"policies[{key!r}] must be a mapping"
        raise ValueError(msg)
    return value


def _positive_int(raw: dict[str, object], key: str, *, default: int) -> int:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return default
    return value


def _positive_float(raw: dict[str, object], key: str, *, default: float) -> float:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float) or value < 0:
        return default
    return float(value)
