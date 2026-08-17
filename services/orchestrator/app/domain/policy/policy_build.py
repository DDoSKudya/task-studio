from __future__ import annotations

from app.domain.policy.policy_parse import positive_float, positive_int, require_mapping
from app.domain.policy.policy_types import (
    BalancingPolicy,
    LspPolicy,
    ManagedServices,
    MaximumPolicy,
    OllamaPolicy,
    PowerSavingPolicy,
)


def build_balancing_policy(balancing: dict[str, object]) -> BalancingPolicy:
    meili = require_mapping(balancing, "meilisearch")
    ollama = require_mapping(balancing, "ollama")
    return BalancingPolicy(
        ollama=OllamaPolicy(
            idle_stop_minutes=positive_int(
                ollama,
                "idle_stop_minutes",
                default=30,
            ),
            min_free_ram_mb=positive_int(
                ollama,
                "min_free_ram_mb",
                default=1536,
            ),
        ),
        lsp=LspPolicy(
            idle_stop_minutes=positive_int(
                require_mapping(balancing, "lsp"),
                "idle_stop_minutes",
                default=15,
            ),
        ),
        meilisearch_pause_below_ram_mb=positive_int(
            meili,
            "pause_indexing_below_ram_mb",
            default=1536,
        ),
        grading_cpu_defer_ollama=positive_float(
            balancing,
            "grading_cpu_defer_ollama",
            default=0.5,
        ),
    )


def build_maximum_policy(maximum: dict[str, object]) -> MaximumPolicy:
    return MaximumPolicy(
        min_free_ram_warning_mb=positive_int(
            maximum,
            "min_free_ram_warning_mb",
            default=1638,
        ),
    )


def build_power_saving_policy(power_saving: dict[str, object]) -> PowerSavingPolicy:
    return PowerSavingPolicy(
        allow_background_import=bool(power_saving.get("allow_background_import", False)),
        analytics_batch_sleep_seconds=positive_int(
            power_saving,
            "analytics_batch_sleep_seconds",
            default=60,
        ),
    )


def build_managed_services(managed: dict[str, object]) -> ManagedServices:
    lsp_services = managed.get("lsp")
    if not isinstance(lsp_services, list) or not lsp_services:
        msg = "managed_services.lsp must be a non-empty list"
        raise ValueError(msg)
    return ManagedServices(
        ollama=str(managed.get("ollama", "ollama")),
        lab_runner=str(managed.get("lab_runner", "lab-runner")),
        lsp=tuple(str(name) for name in lsp_services),
    )
