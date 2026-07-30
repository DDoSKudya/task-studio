from __future__ import annotations

import ast
import re


def python_functions(code: str) -> list[tuple[str, int | None]]:
    if not code or not code.strip():
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        match = re.search(r"^def\s+([A-Za-z_][\w]*)\s*\(", code, flags=re.MULTILINE)
        return [(match[1], None)] if match else []
    found: list[tuple[str, int | None]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name.startswith("_"):
                continue
            positional = sum(arg.arg not in {"self", "cls"} for arg in node.args.args)
            found.append((node.name, positional))
    return found


def javascript_functions(code: str) -> list[str]:
    if not code or not code.strip():
        return []
    patterns = (
        r"(?:export\s+)?function\s+([A-Za-z_][\w]*)\s*\(",
        r"(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][\w]*)\s*=\s*(?:async\s*)?(?:function\s*)?\(",
        r"(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][\w]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
    )
    names: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, code):
            name = match[1]
            if name and not name.startswith("_") and name not in names:
                names.append(name)
    return names


def go_functions(code: str) -> list[str]:
    if not code or not code.strip():
        return []
    names: list[str] = []
    for match in re.finditer(r"func\s+([A-Z][\w]*)\s*\(", code):
        name = match[1]
        if name != "main" and name not in names:
            names.append(name)
    return names
