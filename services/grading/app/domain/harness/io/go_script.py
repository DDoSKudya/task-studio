from __future__ import annotations

import json

from .cases import IoCase


def go_io_script(
    source: str,
    cases: list[IoCase],
    *,
    entrypoint: str | None,
    setup: str,
) -> str:
    if any(case.run for case in cases):
        raise ValueError("scripted run tests are not supported for Go")
    if not entrypoint:
        raise ValueError(
            "cannot determine function to test — set step.entrypoint or define an "
            "exported Go function matching the template"
        )
    calls: list[str] = []
    for index, case in enumerate(cases):
        assert case.args is not None
        arg_list = ", ".join(go_literal(value) for value in case.args)
        calls.append(
            "\t{\n"
            f"\t\tgot := {entrypoint}({arg_list})\n"
            f"\t\twant := {go_literal(case.expected)}\n"
            "\t\tif got != want {\n"
            f'\t\t\tpanic("test {index} failed")\n'
            "\t\t}\n"
            "\t}\n"
        )
    body = source.rstrip()
    if setup:
        body = setup.rstrip() + "\n\n" + body
    if "package " not in body:
        body = "package main\n\n" + body
    return body + "\n\nfunc main() {\n" + "".join(calls) + "}\n"


def go_literal(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if value is None:
        return "nil"
    return json.dumps(value)
