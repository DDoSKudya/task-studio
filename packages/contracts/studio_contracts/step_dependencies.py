from __future__ import annotations

import re
from typing import Final

_PIP_IMPORT_ALIASES: Final[dict[str, str]] = {
    "PIL": "pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv",
    "jwt": "pyjwt",
}

_PYTHON_STDLIB: Final[frozenset[str]] = frozenset(
    {
        "__future__",
        "abc",
        "argparse",
        "array",
        "ast",
        "asyncio",
        "base64",
        "bisect",
        "builtins",
        "calendar",
        "collections",
        "contextlib",
        "copy",
        "csv",
        "dataclasses",
        "datetime",
        "decimal",
        "enum",
        "functools",
        "gc",
        "hashlib",
        "heapq",
        "html",
        "http",
        "importlib",
        "inspect",
        "io",
        "itertools",
        "json",
        "logging",
        "math",
        "operator",
        "os",
        "pathlib",
        "pdb",
        "pickle",
        "platform",
        "queue",
        "random",
        "re",
        "secrets",
        "shlex",
        "shutil",
        "signal",
        "socket",
        "sqlite3",
        "statistics",
        "string",
        "struct",
        "subprocess",
        "sys",
        "tempfile",
        "textwrap",
        "threading",
        "time",
        "traceback",
        "types",
        "typing",
        "unittest",
        "urllib",
        "uuid",
        "warnings",
        "weakref",
        "xml",
        "zipfile",
    }
)

_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", re.MULTILINE)
_REQUIREMENTS_FENCE_RE = re.compile(
    r"```(?:text|txt|pip|requirements)?\s*\n([\s\S]*?)```",
    re.IGNORECASE,
)
_REQUIREMENT_LINE_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.\-]*(?:\[[^\]]+\])?(?:[><=!~]=?[^\s]+)?$",
)
_DEPENDENCY_SECTION_RE = re.compile(
    r"(?is)"
    r"(?:^|\n)\s*(?:#{1,3}\s*)?"
    r"(?:пример\s+)?(?:зависимост|dependencies?|requirements\.txt|package\.json)"
    r"[^\n]*\n.*?(?=\n\s*(?:#{1,3}\s+|\*\*[^*]+\*\*)|\Z)"
)
_DEPENDENCY_FENCE_RE = re.compile(
    r"(?is)```(?:text|txt|pip|requirements)?\s*\n(?:flask|requests|django|numpy|pandas|pytest|httpx|fastapi)[^\n]*\n```"
)


def _dependency_key(spec: str) -> str:
    return re.split(r"[<>=!\[]", spec, maxsplit=1)[0].strip().casefold()


def _merge_dependency_specs(specs: list[str]) -> list[str]:
    out: list[str] = []
    keys: set[str] = set()
    for spec in normalize_dependency_list(specs):
        key = _dependency_key(spec)
        if key in keys:
            continue
        keys.add(key)
        out.append(spec)
    return out


def normalize_dependency_list(raw: object) -> list[str]:
    if raw is None:
        return []
    items: list[object]
    if isinstance(raw, str):
        items = [line.strip() for line in raw.splitlines() if line.strip()]
    elif isinstance(raw, list):
        items = raw
    else:
        return []

    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            continue
        spec = item.strip()
        if not spec or "\n" in spec or spec in seen:
            continue
        if not _REQUIREMENT_LINE_RE.fullmatch(spec):
            continue
        seen.add(spec)
        out.append(spec)
    return out


def extract_requirements_from_content(content: str) -> list[str]:
    found: list[str] = []
    for match in _REQUIREMENTS_FENCE_RE.finditer(content):
        block = match.group(1)
        for line in block.splitlines():
            spec = line.strip()
            if spec and not spec.startswith("#") and _REQUIREMENT_LINE_RE.fullmatch(spec):
                found.append(spec)
    return normalize_dependency_list(found)


def strip_dependency_examples_from_content(content: str) -> str:
    if not content.strip():
        return content
    cleaned = _DEPENDENCY_SECTION_RE.sub("\n", content)
    cleaned = _DEPENDENCY_FENCE_RE.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def infer_python_dependencies(*sources: str) -> list[str]:
    modules: list[str] = []
    for source in sources:
        if not source.strip():
            continue
        modules.extend(_IMPORT_RE.findall(source))
    specs: list[str] = []
    seen: set[str] = set()
    for module in modules:
        root = module.split(".", 1)[0]
        if root in _PYTHON_STDLIB:
            continue
        pip_name = _PIP_IMPORT_ALIASES.get(root, root)
        if pip_name in seen:
            continue
        seen.add(pip_name)
        specs.append(pip_name)
    return specs


def infer_javascript_dependencies(*sources: str) -> list[str]:
    require_re = re.compile(
        r"""(?:require|import)\s*\(\s*['"]([^'"]+)['"]\s*\)"""
        r"""|(?:import|export)\s+[^'"]*['"]([^'"]+)['"]""",
    )
    specs: list[str] = []
    seen: set[str] = set()
    for source in sources:
        if not source.strip():
            continue
        for match in require_re.finditer(source):
            name = next((group for group in match.groups() if group), None)
            if not name or name.startswith(".") or name.startswith("node:"):
                continue
            pkg = name.split("/", 1)[0]
            if pkg.startswith("@") and "/" in name:
                pkg = "/".join(name.split("/", 2)[:2])
            if pkg in seen:
                continue
            seen.add(pkg)
            specs.append(pkg)
    return specs


def resolve_step_dependencies(
    *,
    runtime: str,
    explicit: object = None,
    template: str = "",
    setup: str = "",
    tests: list[object] | None = None,
    content: str = "",
) -> list[str]:
    deps = normalize_dependency_list(explicit)
    deps.extend(extract_requirements_from_content(content))
    deps = _merge_dependency_specs(deps)

    combined_sources = [template, setup]
    if tests:
        for test in tests:
            if isinstance(test, dict) and isinstance(test.get("run"), str):
                combined_sources.append(test["run"])

    lang = runtime.casefold().strip() or "python"
    if lang in {"python", "python3"}:
        deps = _merge_dependency_specs([*deps, *infer_python_dependencies(*combined_sources)])
    elif lang in {"javascript", "js", "node", "typescript", "ts"}:
        deps = _merge_dependency_specs([*deps, *infer_javascript_dependencies(*combined_sources)])

    return deps


def step_skips_local_dependency_install(step: dict[str, object]) -> bool:
    platform = step.get("source_platform")
    return isinstance(platform, str) and platform.casefold() == "stepik"


def apply_code_step_dependencies(step: dict[str, object]) -> None:
    runtime = step.get("runtime")
    runtime_str = runtime if isinstance(runtime, str) else "python"
    template = step.get("template")
    setup = step.get("setup")
    tests = step.get("tests")
    content = step.get("content")

    deps = resolve_step_dependencies(
        runtime=runtime_str,
        explicit=step.get("dependencies"),
        template=template if isinstance(template, str) else "",
        setup=setup if isinstance(setup, str) else "",
        tests=tests if isinstance(tests, list) else None,
        content=content if isinstance(content, str) else "",
    )
    if deps:
        step["dependencies"] = deps

    if isinstance(content, str):
        cleaned = strip_dependency_examples_from_content(content)
        if cleaned != content:
            step["content"] = cleaned


def python_pip_install_preamble(dependencies: list[str]) -> str:
    if not dependencies:
        return ""
    pkg_literals = ", ".join(repr(spec) for spec in dependencies)
    return (
        "import subprocess\n"
        "import sys\n"
        f"_pkgs = [{pkg_literals}]\n"
        "subprocess.check_call(\n"
        "    [sys.executable, '-m', 'pip', 'install', '-q', "
        "'--disable-pip-version-check', *_pkgs],\n"
        "    stdout=subprocess.DEVNULL,\n"
        "    stderr=subprocess.DEVNULL,\n"
        ")\n"
    )


def javascript_npm_install_preamble(dependencies: list[str]) -> str:
    if not dependencies:
        return ""
    pkg_literals = ", ".join(repr(spec) for spec in dependencies)
    return (
        "const { execSync } = require('child_process');\n"
        "const fs = require('fs');\n"
        "const path = require('path');\n"
        f"const _deps = [{pkg_literals}];\n"
        "if (_deps.length) {\n"
        "  const pkgPath = path.join(process.cwd(), 'package.json');\n"
        "  if (!fs.existsSync(pkgPath)) {\n"
        '    fs.writeFileSync(pkgPath, JSON.stringify({ name: "job", private: true }));\n'
        "  }\n"
        "  execSync(\n"
        "    'npm install --no-save --no-package-lock ' + "
        "_deps.map((d) => JSON.stringify(d)).join(' '),\n"
        "    { stdio: 'ignore' },\n"
        "  );\n"
        "}\n"
    )


def go_get_preamble(dependencies: list[str]) -> str:
    if not dependencies:
        return ""
    lines = ['import (\n\t"os/exec"\n)\n', "func init() {\n"]
    for spec in dependencies:
        lines.append(f'\t_ = exec.Command("go", "get", {spec!r}).Run()\n')
    lines.append("}\n")
    return "".join(lines)


def merge_setup_with_dependencies(
    *,
    language: str,
    setup: str,
    dependencies: list[str],
    skip_install: bool,
) -> str:
    base = setup.strip() if setup.strip() else ""
    if skip_install or not dependencies:
        return base

    lang = language.casefold().strip() or "python"
    preamble = ""
    if lang in {"python", "python3"}:
        preamble = python_pip_install_preamble(dependencies)
    elif lang in {"javascript", "js", "node", "typescript", "ts"}:
        preamble = javascript_npm_install_preamble(dependencies)
    elif lang in {"go", "golang"}:
        preamble = go_get_preamble(dependencies)

    if not preamble:
        return base
    if base:
        return f"{preamble.rstrip()}\n\n{base}"
    return preamble.rstrip()
