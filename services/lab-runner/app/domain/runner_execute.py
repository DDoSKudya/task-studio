from __future__ import annotations

import contextlib
import subprocess
import uuid
from pathlib import Path

from app.config import LabRunnerSettings
from app.domain.compose_exec import docker_compose, run_check, timeout_seconds
from app.domain.runner_types import LabRunOutcome, elapsed_ms, failed_outcome


def execute_lab_checks(
    settings: LabRunnerSettings,
    *,
    pack_root: str,
    step: dict[str, object],
    compose_file: str,
    checks: list[object],
    started: float,
) -> LabRunOutcome:
    compose_path = Path(pack_root) / compose_file
    if not compose_path.is_file():
        return failed_outcome(f"compose file not found: {compose_file}", started)

    timeout = timeout_seconds(step, settings.default_timeout_seconds)
    project_name = f"lab_{uuid.uuid4().hex[:12]}"

    try:
        docker_compose(compose_path, project_name, "up", "-d", "--wait", timeout=timeout)
        for index, check in enumerate(checks):
            if not isinstance(check, dict):
                return failed_outcome(f"invalid check at index {index}", started)
            if not run_check(check, compose_path, project_name, timeout):
                return failed_outcome(f"check {index} failed", started)
        return LabRunOutcome(
            passed=True,
            score=1.0,
            feedback=None,
            details={"checks_passed": len(checks)},
            duration_ms=elapsed_ms(started),
        )
    except subprocess.TimeoutExpired:
        return failed_outcome("lab timed out", started)
    except OSError as exc:
        return failed_outcome(f"lab runner error: {exc}", started)
    finally:
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            docker_compose(
                compose_path,
                project_name,
                "down",
                "--volumes",
                "--remove-orphans",
                timeout=60,
            )
