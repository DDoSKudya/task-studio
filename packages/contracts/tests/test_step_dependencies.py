from __future__ import annotations

from studio_contracts.step_dependencies import (
    apply_code_step_dependencies,
    merge_setup_with_dependencies,
    normalize_dependency_list,
    resolve_step_dependencies,
    strip_dependency_examples_from_content,
)


def test_normalize_dependency_list_dedupes_and_validates() -> None:
    assert normalize_dependency_list(["requests==2.31.0", "requests==2.31.0", ""]) == [
        "requests==2.31.0"
    ]
    assert normalize_dependency_list("flask>=3.0\n\nhttpx") == ["flask>=3.0", "httpx"]
    assert normalize_dependency_list(["not valid spec!!"]) == []


def test_strip_dependency_examples_from_content() -> None:
    raw = (
        "## Goal\nWrite a handler.\n\n"
        "### Пример зависимости в requirements.txt\n"
        "```text\nflask==3.0.0\nrequests\n```\n\n"
        "## Constraints\nstdlib only for parsing."
    )
    cleaned = strip_dependency_examples_from_content(raw)
    assert "requirements.txt" not in cleaned
    assert "flask==3.0.0" not in cleaned
    assert "Write a handler" in cleaned


def test_resolve_step_dependencies_from_imports_and_content() -> None:
    deps = resolve_step_dependencies(
        runtime="python",
        template="import requests\nfrom flask import Flask\n\ndef solve():\n    pass\n",
        content="```text\npytest>=8.0\n```",
    )
    assert "requests" in deps
    assert "flask" in deps
    assert "pytest>=8.0" in deps
    assert "os" not in deps


def test_apply_code_step_dependencies_mutates_step() -> None:
    step: dict[str, object] = {
        "kind": "code",
        "runtime": "python",
        "content": (
            "Do the thing.\n\n### Пример зависимости в requirements.txt\n```text\nrequests\n```"
        ),
        "template": "import httpx\n\ndef solve():\n    return httpx.get('https://example.com')\n",
        "tests": [{"input": [], "output": 200}],
    }
    apply_code_step_dependencies(step)
    assert isinstance(step.get("dependencies"), list)
    assert "httpx" in step["dependencies"]
    assert "requests" not in str(step.get("content"))


def test_merge_setup_with_dependencies_python_preamble() -> None:
    merged = merge_setup_with_dependencies(
        language="python",
        setup="x = 1",
        dependencies=["requests"],
        skip_install=False,
    )
    assert "pip', 'install'" in merged or 'pip", "install"' in merged
    assert "x = 1" in merged


def test_merge_setup_with_dependencies_skips_stepik() -> None:
    merged = merge_setup_with_dependencies(
        language="python",
        setup="x = 1",
        dependencies=["requests"],
        skip_install=True,
    )
    assert merged == "x = 1"
    assert "pip" not in merged
