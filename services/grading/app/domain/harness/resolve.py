from __future__ import annotations

from app.domain.executable import step_checker_mode, step_tests_are_executable
from app.domain.harness.pick import pick_harness_job
from app.domain.harness.resolve_types import HarnessBlocked, HarnessJob

__all__ = ["HarnessJob", "HarnessBlocked", "resolve_harness"]


def resolve_harness(step: dict[str, object], source: str) -> HarnessJob | HarnessBlocked | None:
    if step_checker_mode(step) == "llm":
        return None

    tests = step.get("tests")
    has_tests = isinstance(tests, list) and bool(tests)
    test_source = step.get("test_source")
    has_test_source = isinstance(test_source, str) and bool(test_source.strip())
    fcc_tests = step.get("fcc_tests")
    has_fcc_tests = isinstance(fcc_tests, list) and bool(fcc_tests)

    if has_test_source or has_fcc_tests or (has_tests and step_tests_are_executable(step)):
        return pick_harness_job(
            step,
            source,
            has_test_source=has_test_source,
            has_fcc_tests=has_fcc_tests,
            test_source=test_source,
            fcc_tests=fcc_tests,
            tests=tests,
        )
    return None
