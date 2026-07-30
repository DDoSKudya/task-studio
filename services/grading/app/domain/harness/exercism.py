from __future__ import annotations

import re

from .shared import PistonJob


def build_exercism_job(
    *,
    runtime: str,
    source: str,
    test_source: str,
    solution_file: str | None = None,
    test_file: str | None = None,
) -> PistonJob | None:
    lang = runtime.casefold().strip() or "python"
    if lang in {"python", "python3"}:
        solution_name = _python_solution_name(test_source, solution_file)
        test_name = (
            test_file.strip()
            if isinstance(test_file, str) and test_file.strip()
            else f"{solution_name.removesuffix('.py')}_test.py"
        )
        runner = (
            "import unittest\n"
            f"unittest.main(module={_module_name(test_name)!r}, verbosity=2, exit=True)\n"
        )
        return PistonJob(
            language="python",
            version="3.12",
            files=[
                {"name": "main.py", "content": runner},
                {"name": solution_name, "content": source},
                {"name": test_name, "content": test_source},
            ],
        )

    return None


def _python_solution_name(test_source: str, solution_file: str | None) -> str:
    if isinstance(solution_file, str) and solution_file.strip():
        return solution_file.strip()
    match = re.search(r"from\s+([A-Za-z_][\w]*)\s+import", test_source)
    if match:
        return f"{match[1]}.py"
    match = re.search(r"import\s+([A-Za-z_][\w]*)", test_source)
    if match and match[1] not in {"unittest", "pytest", "sys", "os"}:
        return f"{match[1]}.py"
    return "solution.py"


def _module_name(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1]
    if name.endswith(".py"):
        return name[:-3]
    return name
