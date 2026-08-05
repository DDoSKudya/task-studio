from __future__ import annotations

import subprocess
from pathlib import Path


def compose_service_name(check: dict[str, object]) -> str:
    service = check.get("service")
    if isinstance(service, str) and service.strip():
        return service.strip()
    return "app"


def run_check(
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
    expected = expected_exit_code(check)
    service = compose_service_name(check)
    result = subprocess.run(
        compose_command(compose_path, project_name, "exec", "-T", service, "sh", "-lc", command),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return result.returncode == expected


def docker_compose(
    compose_path: Path,
    project_name: str,
    *args: str,
    timeout: int,
) -> None:
    subprocess.run(
        compose_command(compose_path, project_name, *args),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=True,
    )


def compose_command(compose_path: Path, project_name: str, *args: str) -> list[str]:
    return ["docker", "compose", "-f", str(compose_path), "-p", project_name, *args]


def expected_exit_code(check: dict[str, object]) -> int:
    expected = check.get("expect_exit_code", 0)
    if isinstance(expected, int) and not isinstance(expected, bool):
        return expected
    return 0


def timeout_seconds(step: dict[str, object], default: int) -> int:
    raw = step.get("timeout_seconds")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    return default
