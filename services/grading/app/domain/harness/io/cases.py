from __future__ import annotations

from dataclasses import dataclass

from .entrypoint_lang import go_functions, javascript_functions, python_functions
from .entrypoint_resolve import pick_python_by_arity, resolve_entrypoint

__all__ = [
    "IoCase",
    "normalize_io_tests",
    "first_arity",
    "resolve_entrypoint",
    "pick_python_by_arity",
    "python_functions",
    "javascript_functions",
    "go_functions",
]


@dataclass(frozen=True, slots=True)
class IoCase:
    args: list[object] | None = None
    expected: object = None
    run: str | None = None


def normalize_io_tests(tests: list[object]) -> list[IoCase]:
    cases: list[IoCase] = []
    for item in tests:
        if not isinstance(item, dict):
            continue
        run = item.get("run")
        if isinstance(run, str) and run.strip():
            cases.append(IoCase(run=run.strip()))
            continue
        args = item.get("input")
        if not isinstance(args, list):
            continue
        cases.append(IoCase(args=args, expected=item.get("output")))
    return cases


def first_arity(cases: list[IoCase]) -> int | None:
    for case in cases:
        if case.args is not None:
            return len(case.args)
    return None
