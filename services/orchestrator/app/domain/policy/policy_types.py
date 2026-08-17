from __future__ import annotations

from dataclasses import dataclass


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
