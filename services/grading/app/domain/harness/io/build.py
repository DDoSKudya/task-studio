from __future__ import annotations

from studio_contracts.step_dependencies import (
    merge_setup_with_dependencies,
    normalize_dependency_list,
)

from ..shared import PistonJob
from .cases import first_arity, normalize_io_tests, resolve_entrypoint
from .go_script import go_io_script
from .js_script import javascript_io_script
from .python_script import python_io_script


def build_io_job(
    *,
    language: str,
    version: str,
    source: str,
    tests: list[object],
    entrypoint: str | None = None,
    template: str | None = None,
    setup: str | None = None,
    dependencies: list[str] | None = None,
    skip_dependency_install: bool = False,
) -> PistonJob:
    lang = language.casefold().strip() or "python"
    cases = normalize_io_tests(tests)
    if not cases:
        raise ValueError("code step tests are invalid")

    resolved = resolve_entrypoint(
        language=lang,
        source=source,
        template=template,
        entrypoint=entrypoint,
        arity=first_arity(cases),
    )
    setup_code = setup.strip() if isinstance(setup, str) and setup.strip() else ""
    deps = normalize_dependency_list(dependencies or [])
    setup_code = merge_setup_with_dependencies(
        language=lang,
        setup=setup_code,
        dependencies=deps,
        skip_install=skip_dependency_install,
    )

    if lang in {"python", "python3"}:
        return PistonJob(
            language="python",
            version=version or "3.12",
            files=[
                {
                    "name": "main.py",
                    "content": python_io_script(
                        source,
                        cases,
                        entrypoint=resolved,
                        setup=setup_code,
                    ),
                }
            ],
        )
    if lang in {"javascript", "js", "node", "typescript"}:
        return PistonJob(
            language="javascript",
            version=version if version and version != "latest" else "18.15.0",
            files=[
                {
                    "name": "main.js",
                    "content": javascript_io_script(
                        source,
                        cases,
                        entrypoint=resolved,
                        setup=setup_code,
                    ),
                }
            ],
        )
    if lang in {"go", "golang"}:
        return PistonJob(
            language="go",
            version=version if version and version != "latest" else "*",
            files=[
                {
                    "name": "main.go",
                    "content": go_io_script(
                        source,
                        cases,
                        entrypoint=resolved,
                        setup=setup_code,
                    ),
                }
            ],
        )
    raise ValueError(f"unsupported runtime for I/O tests: {language}")
