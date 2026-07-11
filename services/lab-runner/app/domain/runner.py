from __future__ import annotations

import contextlib
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.config import LabRunnerSettings


@dataclass(frozen=True, slots=True)
class LabRunOutcome:
    passed: bool
    score: float
    feedback: str | None
    details: dict[str, object]
    duration_ms: int


def run_lab(
    settings: LabRunnerSettings,
    *,
    pack_root: str,
    step: dict[str, object],
) -> LabRunOutcome:
    started = time.perf_counter()
    compose_file = step.get("compose_file")
    if not isinstance(compose_file, str) or not compose_file.strip():
        return _failed("lab step missing compose_file", started)

    checks = step.get("checks")
    if not isinstance(checks, list) or not checks:
        return _failed("lab step missing checks", started)

    if settings.dry_run:
        return LabRunOutcome(
            passed=True,
            score=1.0,
            feedback=None,
            details={"mode": "dry_run", "checks": len(checks), "compose_file": compose_file},
            duration_ms=_elapsed_ms(started),
        )

    compose_path = Path(pack_root) / compose_file
    if not compose_path.is_file():
        return _failed(f"compose file not found: {compose_file}", started)

    timeout = _timeout_seconds(step, settings.default_timeout_seconds)
    project_name = f"lab_{uuid.uuid4().hex[:12]}"

    try:
        _docker_compose(compose_path, project_name, "up", "-d", "--wait", timeout=timeout)
        for index, check in enumerate(checks):
            if not isinstance(check, dict):
                return _failed(f"invalid check at index {index}", started)
            if not _run_check(check, compose_path, project_name, timeout):
                return _failed(f"check {index} failed", started)
        return LabRunOutcome(
            passed=True,
            score=1.0,
            feedback=None,
            details={"checks_passed": len(checks)},
            duration_ms=_elapsed_ms(started),
        )
    except subprocess.TimeoutExpired:
        return _failed("lab timed out", started)
    except OSError as exc:
        return _failed(f"lab runner error: {exc}", started)
    finally:
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            _docker_compose(
                compose_path,
                project_name,
                "down",
                "--volumes",
                "--remove-orphans",
                timeout=60,
            )


def _run_check(
    check: dict[str, object],
    compose_path: Path,
    project_name: str,
    timeout: int,
) -> bool:
    if check.get("type") != "command":
        return False
    command = check.get("command")
    if not isinstance(command, str) or not command.strip():
        return False
    expected = _expected_exit_code(check)
    result = subprocess.run(
        _compose_command(compose_path, project_name, "exec", "-T", "app", "sh", "-lc", command),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return result.returncode == expected


def _docker_compose(
    compose_path: Path,
    project_name: str,
    *args: str,
    timeout: int,
) -> None:
    subprocess.run(
        _compose_command(compose_path, project_name, *args),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )


def _compose_command(compose_path: Path, project_name: str, *args: str) -> list[str]:
    return ["docker", "compose", "-f", str(compose_path), "-p", project_name, *args]


def _expected_exit_code(check: dict[str, object]) -> int:
    expected = check.get("expect_exit_code", 0)
    if isinstance(expected, int) and not isinstance(expected, bool):
        return expected
    return 0


def _timeout_seconds(step: dict[str, object], default: int) -> int:
    raw = step.get("timeout_seconds")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    return default


def _failed(message: str, started: float) -> LabRunOutcome:
    return LabRunOutcome(
        passed=False,
        score=0.0,
        feedback=message,
        details={"error": message},
        duration_ms=_elapsed_ms(started),
    )


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)
