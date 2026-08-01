from __future__ import annotations

from app.domain.executable.fixtures import SUPPORTED_IO_RUNTIMES, args_need_fixtures


def step_checker_mode(step: dict[str, object]) -> str:
    raw = step.get("checker")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().casefold()
    return "auto"


def step_tests_are_executable(step: dict[str, object]) -> bool:
    mode = step_checker_mode(step)
    if mode == "llm":
        return False
    if mode == "piston":
        return True

    test_source = step.get("test_source")
    if isinstance(test_source, str) and test_source.strip():
        return True

    fcc_tests = step.get("fcc_tests")
    if isinstance(fcc_tests, list) and bool(fcc_tests):
        return True

    tests = step.get("tests")
    if not isinstance(tests, list) or not tests:
        return False

    runtime = step.get("runtime")
    lang = runtime.casefold().strip() if isinstance(runtime, str) else "python"
    if lang not in SUPPORTED_IO_RUNTIMES:
        return False

    setup = step.get("setup")
    has_setup = isinstance(setup, str) and bool(setup.strip())

    usable = 0
    for item in tests:
        if not isinstance(item, dict):
            continue
        run = item.get("run")
        if isinstance(run, str) and run.strip():
            usable += 1
            continue
        args = item.get("input")
        if not isinstance(args, list) or "output" not in item:
            continue
        if args_need_fixtures(args) and not has_setup:
            return False
        usable += 1
    return usable > 0
