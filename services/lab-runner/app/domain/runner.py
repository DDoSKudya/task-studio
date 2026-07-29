from __future__ import annotations

import time

from app.config import LabRunnerSettings
from app.domain.runner_execute import execute_lab_checks
from app.domain.runner_types import LabRunOutcome, failed_outcome

__all__ = ["LabRunOutcome", "run_lab"]


def run_lab(
    settings: LabRunnerSettings,
    *,
    pack_root: str,
    step: dict[str, object],
) -> LabRunOutcome:
    started = time.perf_counter()
    compose_file = step.get("compose_file")
    if not isinstance(compose_file, str) or not compose_file.strip():
        return failed_outcome("lab step missing compose_file", started)

    checks = step.get("checks")
    if not isinstance(checks, list) or not checks:
        return failed_outcome("lab step missing checks", started)

    if settings.dry_run:
        return LabRunOutcome(
            passed=True,
            score=1.0,
            feedback=None,
            details={"mode": "dry_run", "checks": len(checks), "compose_file": compose_file},
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    return execute_lab_checks(
        settings,
        pack_root=pack_root,
        step=step,
        compose_file=compose_file,
        checks=checks,
        started=started,
    )
