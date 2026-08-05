from __future__ import annotations

from app.domain.check.outcome import optional_str
from app.domain.harness.exercism import build_exercism_job
from app.domain.harness.fcc import build_fcc_job
from app.domain.harness.io import build_io_job
from app.domain.harness.resolve_types import HarnessBlocked, HarnessJob
from studio_contracts.step_dependencies import (
    normalize_dependency_list,
    step_skips_local_dependency_install,
)


def pick_harness_job(
    step: dict[str, object],
    source: str,
    *,
    has_test_source: bool,
    has_fcc_tests: bool,
    test_source: object,
    fcc_tests: object,
    tests: object,
) -> HarnessJob | HarnessBlocked:
    runtime = step.get("runtime")
    runtime_version = step.get("runtime_version")
    language = runtime if isinstance(runtime, str) else "python"
    version = runtime_version if isinstance(runtime_version, str) else "3.12"

    if has_test_source:
        job = build_exercism_job(
            runtime=language,
            source=source,
            test_source=str(test_source),
            solution_file=optional_str(step.get("solution_file")),
            test_file=optional_str(step.get("test_file")),
        )
        if job is None:
            return HarnessBlocked(
                checker="exercism",
                reason="exercism harness unavailable",
                ungradable=(
                    f"Exercism auto-check is unavailable for runtime={language!r} "
                    "(needs a track test harness; Python/unittest is supported)."
                ),
            )
        return HarnessJob(job=job, checker="exercism")

    if has_fcc_tests:
        if not isinstance(fcc_tests, list):
            return HarnessBlocked(
                checker="fcc",
                reason="fcc harness unavailable",
                ungradable="freeCodeCamp auto-check is unavailable for this step.",
            )
        job = build_fcc_job(runtime=language, source=source, fcc_tests=fcc_tests)
        if job is None:
            return HarnessBlocked(
                checker="fcc",
                reason="fcc harness unavailable",
                ungradable=(
                    "freeCodeCamp auto-check is unavailable for this step "
                    "(needs a browser/DOM runner)."
                ),
            )
        return HarnessJob(job=job, checker="fcc")

    if not isinstance(tests, list):
        return HarnessBlocked(
            checker="piston",
            reason="invalid tests payload",
            ungradable="Code tests payload is invalid.",
        )
    try:
        job = build_io_job(
            language=language,
            version=version,
            source=source,
            tests=tests,
            entrypoint=optional_str(step.get("entrypoint")),
            template=optional_str(step.get("template")),
            setup=optional_str(step.get("setup")),
            dependencies=normalize_dependency_list(step.get("dependencies")),
            skip_dependency_install=step_skips_local_dependency_install(step),
        )
    except ValueError as exc:
        return HarnessBlocked(
            checker="piston",
            reason=str(exc),
            ungradable=str(exc),
        )
    return HarnessJob(job=job, checker="piston")
