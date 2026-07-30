from __future__ import annotations

import json

from .cases import IoCase


def javascript_io_script(
    source: str,
    cases: list[IoCase],
    *,
    entrypoint: str | None,
    setup: str,
) -> str:
    io_cases = [
        {"input": case.args, "output": case.expected}
        for case in cases
        if case.run is None and case.args is not None
    ]
    run_cases = [case.run for case in cases if case.run is not None]
    if io_cases and not entrypoint:
        raise ValueError(
            "cannot determine function to test — set step.entrypoint or define one "
            "top-level function matching the template"
        )

    chunks: list[str] = []
    if setup:
        chunks.append(setup.rstrip())
        chunks.append("")
    chunks.append(source.rstrip())
    chunks.append("")
    chunks.append("const __assert = require('assert');")
    if io_cases:
        assert entrypoint is not None
        name_lit = json.dumps(entrypoint)

        chunks.append(f"const __cases = {json.dumps(io_cases, ensure_ascii=False)};")
        chunks.append(
            f"let __solve = (typeof {entrypoint} === 'function') ? {entrypoint} : null;\n"
            "if (typeof __solve !== 'function' && typeof module !== 'undefined' "
            f"&& module.exports && typeof module.exports[{name_lit}] === 'function') {{\n"
            f"  __solve = module.exports[{name_lit}];\n"
            "}\n"
            "if (typeof __solve !== 'function') {\n"
            f"  throw new Error('solution must define {entrypoint}(...)');\n"
            "}\n"
            "function __expandArg(value) {\n"
            "  if (value && typeof value === 'object' && typeof value.$call === 'string') {\n"
            "    const fn = eval(value.$call);\n"
            "    if (typeof fn !== 'function') throw new Error(`unknown fixture ${value.$call}`);\n"
            "    return fn();\n"
            "  }\n"
            "  return value;\n"
            "}\n"
            "for (let i = 0; i < __cases.length; i += 1) {\n"
            "  const c = __cases[i];\n"
            "  const args = c.input.map(__expandArg);\n"
            "  const actual = __solve(...args);\n"
            "  __assert.deepStrictEqual(actual, c.output, `test ${i} failed`);\n"
            "}"
        )
    for index, run in enumerate(run_cases):
        if not run:
            continue
        chunks.append(f"// scripted test {index}\n{run}")
    chunks.append("")
    return "\n".join(chunks)
