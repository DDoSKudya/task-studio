from __future__ import annotations

import re

from .cases import IoCase


def python_io_script(
    source: str,
    cases: list[IoCase],
    *,
    entrypoint: str | None,
    setup: str,
) -> str:
    parts: list[str] = []
    if setup:
        parts.extend([setup.rstrip(), ""])
    parts.extend([source.rstrip(), "", "def __run_tests():"])

    needs_entrypoint = any(case.run is None for case in cases)
    if needs_entrypoint and not entrypoint:
        raise ValueError(
            "cannot determine function to test — set step.entrypoint or define one "
            "top-level function matching the template"
        )

    for index, case in enumerate(cases):
        if case.run is not None:
            for line in case.run.splitlines() or ["pass"]:
                parts.append(f"    {line}")
            continue
        assert entrypoint is not None and case.args is not None
        arg_literals = ", ".join(python_arg_expr(value) for value in case.args)
        parts.append(
            f"    assert {entrypoint}({arg_literals}) == {case.expected!r}, 'test {index} failed'"
        )

    parts.extend(["", "__run_tests()", ""])
    return "\n".join(parts)


def python_arg_expr(value: object) -> str:
    if isinstance(value, dict) and set(value) == {"$call"}:
        name = value.get("$call")
        if isinstance(name, str) and re.fullmatch(r"[A-Za-z_][\w]*", name):
            return f"{name}()"
    return repr(value)
