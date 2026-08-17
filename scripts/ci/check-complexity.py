#!/usr/bin/env python3

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".nuxt",
    ".output",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    ".venv",
    "__pycache__",
    "data",
    "dist",
    "node_modules",
    "prompts",
    "site-packages",
}

MAX_LINES = 80
MAX_COMPLEXITY = 15
MAX_PARAMS = 8
MAX_NEST = 4
MUST_LINES = 120
MUST_COMPLEXITY = 25
MAX_CLASS_LINES = 400
MUST_CLASS_LINES = 500
MAX_CLASS_METHODS = 20


class Finding(NamedTuple):
    path: Path
    line: int
    name: str
    kind: str
    metric: str
    value: int
    limit: int
    must: bool


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def is_test_path(path: Path) -> bool:
    parts = set(path.parts)
    name = path.name
    return (
        "tests" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def cyclomatic_complexity(node: ast.AST) -> int:
    score = 1
    for child in ast.walk(node):
        if isinstance(
            child,
            ast.If
            | ast.For
            | ast.AsyncFor
            | ast.While
            | ast.ExceptHandler
            | ast.With
            | ast.AsyncWith
            | ast.Assert
            | ast.comprehension,
        ):
            score += 1
        elif isinstance(child, ast.BoolOp):
            score += max(0, len(child.values) - 1)
        elif isinstance(child, ast.IfExp):
            score += 1
    return score


def max_nesting(node: ast.AST, depth: int = 0) -> int:
    deepest = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(
            child,
            ast.If
            | ast.For
            | ast.AsyncFor
            | ast.While
            | ast.With
            | ast.AsyncWith
            | ast.Try
            | ast.ExceptHandler,
        ):
            deepest = max(deepest, max_nesting(child, depth + 1))
        else:
            deepest = max(deepest, max_nesting(child, depth))
    return deepest


def parameter_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    args = node.args
    return (
        len(args.posonlyargs)
        + len(args.args)
        + len(args.kwonlyargs)
        + (1 if args.vararg else 0)
        + (1 if args.kwarg else 0)
    )


def iter_python_files() -> Iterable[Path]:
    for path in ROOT.rglob("*.py"):
        if is_skipped(path):
            continue
        yield path


def analyze_function(
    path: Path,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    treat_as_test: bool,
) -> list[Finding]:
    if node.end_lineno is None:
        return []
    lines = node.end_lineno - node.lineno + 1
    complexity = cyclomatic_complexity(node)
    params = parameter_count(node)
    nesting = max((max_nesting(body, 1) for body in node.body), default=0)
    findings: list[Finding] = []
    checks = (
        ("lines", lines, MAX_LINES, MUST_LINES),
        ("complexity", complexity, MAX_COMPLEXITY, MUST_COMPLEXITY),
        ("params", params, MAX_PARAMS, MAX_PARAMS + 1 if treat_as_test else MAX_PARAMS),
        ("nesting", nesting, MAX_NEST, MAX_NEST + 1 if treat_as_test else MAX_NEST),
    )
    for metric, value, soft_limit, must_limit in checks:
        if value <= soft_limit:
            continue
        must = (not treat_as_test) and value > must_limit and metric in {"lines", "complexity"}
        if treat_as_test and metric in {"params", "nesting"}:
            continue
        if treat_as_test and not (value > must_limit and metric in {"lines", "complexity"}):
            continue
        findings.append(
            Finding(
                path=path.relative_to(ROOT),
                line=node.lineno,
                name=node.name,
                kind="function",
                metric=metric,
                value=value,
                limit=must_limit if must else soft_limit,
                must=must,
            )
        )
    return findings


def analyze_class(path: Path, node: ast.ClassDef, *, treat_as_test: bool) -> list[Finding]:
    if node.end_lineno is None or treat_as_test:
        return []
    lines = node.end_lineno - node.lineno + 1
    methods = sum(
        1 for child in node.body if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
    )
    findings: list[Finding] = []
    if lines > MAX_CLASS_LINES:
        findings.append(
            Finding(
                path=path.relative_to(ROOT),
                line=node.lineno,
                name=node.name,
                kind="class",
                metric="lines",
                value=lines,
                limit=MUST_CLASS_LINES if lines > MUST_CLASS_LINES else MAX_CLASS_LINES,
                must=lines > MUST_CLASS_LINES,
            )
        )
    if methods > MAX_CLASS_METHODS:
        findings.append(
            Finding(
                path=path.relative_to(ROOT),
                line=node.lineno,
                name=node.name,
                kind="class",
                metric="methods",
                value=methods,
                limit=MAX_CLASS_METHODS,
                must=False,
            )
        )
    return findings


def analyze_file(path: Path) -> list[Finding]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []
    treat_as_test = is_test_path(path)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            findings.extend(analyze_function(path, node, treat_as_test=treat_as_test))
        elif isinstance(node, ast.ClassDef):
            findings.extend(analyze_class(path, node, treat_as_test=treat_as_test))
    return findings


def main(argv: list[str]) -> int:
    strict = "--strict" in argv
    findings: list[Finding] = []
    for path in iter_python_files():
        findings.extend(analyze_file(path))
    must = [item for item in findings if item.must]
    soft = [item for item in findings if not item.must]
    must.sort(key=lambda item: (-item.value, str(item.path), item.line))
    soft.sort(key=lambda item: (-item.value, str(item.path), item.line))

    print(
        "complexity thresholds: "
        f"func lines soft={MAX_LINES} must={MUST_LINES}; "
        f"complexity soft={MAX_COMPLEXITY} must={MUST_COMPLEXITY}; "
        f"params soft={MAX_PARAMS}; nesting soft={MAX_NEST}"
    )
    print(f"must={len(must)} soft={len(soft)}")
    for item in must[:80]:
        print(
            f"MUST {item.path}:{item.line} {item.kind} {item.name} "
            f"{item.metric}={item.value}>{item.limit}"
        )
    if len(must) > 80:
        print(f"... and {len(must) - 80} more MUST")
    if soft and not strict:
        print(f"soft sample ({min(20, len(soft))} of {len(soft)}):")
        for item in soft[:20]:
            print(
                f"SOFT {item.path}:{item.line} {item.kind} {item.name} "
                f"{item.metric}={item.value}>{item.limit}"
            )

    if must:
        return 1
    if strict and soft:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
