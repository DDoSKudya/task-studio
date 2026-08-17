from __future__ import annotations

from pathlib import Path

import yaml
from app.domain.policy.policy_build import (
    build_balancing_policy,
    build_managed_services,
    build_maximum_policy,
    build_power_saving_policy,
)
from app.domain.policy.policy_parse import positive_int, require_mapping
from app.domain.policy.policy_types import (
    BalancingPolicy,
    LspPolicy,
    ManagedServices,
    MaximumPolicy,
    OllamaPolicy,
    OrchestratorPolicies,
    PowerSavingPolicy,
)

__all__ = [
    "OllamaPolicy",
    "LspPolicy",
    "BalancingPolicy",
    "MaximumPolicy",
    "PowerSavingPolicy",
    "ManagedServices",
    "OrchestratorPolicies",
    "load_policies",
]


def load_policies(path: str | Path) -> OrchestratorPolicies:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = "policies file must be a mapping"
        raise ValueError(msg)

    balancing = require_mapping(raw, "balancing")
    maximum = require_mapping(raw, "maximum")
    power_saving = require_mapping(raw, "power_saving")
    managed = require_mapping(raw, "managed_services")

    return OrchestratorPolicies(
        balancing=build_balancing_policy(balancing),
        maximum=build_maximum_policy(maximum),
        power_saving=build_power_saving_policy(power_saving),
        loop_interval_seconds=positive_int(raw, "loop_interval_seconds", default=30),
        managed_services=build_managed_services(managed),
    )
