from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```([^\n`]*)\n([\s\S]*?)```", re.MULTILINE)

_FENCE_LINE_RE = re.compile(r"^\s*(`{2,})([A-Za-z][\w+-]*)?\s*$")


def _repair_code_fences(markdown: str) -> str:
    if not markdown or "`" not in markdown:
        return markdown

    lines = markdown.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    fence_count = 0
    for line in lines:
        match = _FENCE_LINE_RE.match(line.rstrip())
        if match:
            lang = match.group(2) or ""
            out.append(f"```{lang}" if lang else "```")
            fence_count += 1
            continue
        out.append(line)

    if fence_count % 2 == 1:
        out.append("```")
    return "\n".join(out)


def _looks_like_python(code: str) -> bool:
    if re.search(r"^\s*(?:async\s+)?def\s+\w+", code, re.MULTILINE):
        return True
    if re.search(r"^\s*class\s+\w+", code, re.MULTILINE):
        return True
    if re.search(r"^\s*(?:from\s+\S+\s+import|import\s+\S+)", code, re.MULTILINE):
        return True
    if re.search(r"^\s*print\s*\(", code, re.MULTILINE):
        return True

    if re.search(r"^\s*with\s+.+\s+as\s+\w+\s*:", code, re.MULTILINE | re.IGNORECASE):
        return True
    if re.search(
        r"\b(?:session|engine)\.(?:add|commit|flush|execute|query|scalars|get|rollback)\s*\(",
        code,
        re.IGNORECASE,
    ):
        return True
    return bool(
        re.search(r"^\s*\w+\s*=\s*[A-Z]\w*\s*\(", code, re.MULTILINE)
        and re.search(r"\.\w+\s*\(", code)
    )


def _looks_like_sql(code: str) -> bool:
    if re.search(
        r"^\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE)\b",
        code,
        re.IGNORECASE | re.MULTILINE,
    ):
        return True
    return bool(re.search(r"^\s*WITH\s+\w+\s+AS\s*\(", code, re.IGNORECASE | re.MULTILINE))


def _infer_fence_language(code: str, hinted: str) -> str:
    hint = hinted.strip().lower().split()[0] if hinted.strip() else ""
    aliases = {
        "py": "python",
        "python": "python",
        "python3": "python",
        "js": "javascript",
        "javascript": "javascript",
        "ts": "typescript",
        "typescript": "typescript",
        "sql": "sql",
        "postgresql": "sql",
        "postgres": "sql",
        "mysql": "sql",
        "sqlite": "sql",
        "mermaid": "mermaid",
        "text": "text",
        "plain": "text",
        "plaintext": "text",
    }
    hint = aliases.get(hint, hint)
    if hint == "mermaid":
        return "mermaid"
    python = _looks_like_python(code)
    sql = _looks_like_sql(code)
    if hint == "sql" and python and not sql:
        return "python"
    if hint in {"text", "plain", "plaintext", ""}:
        if python:
            return "python"
        if sql:
            return "sql"
        return hint or "text"
    if hint:
        return hint
    if python:
        return "python"
    if sql:
        return "sql"
    return "text"


def _retarget_code_fences(markdown: str) -> str:
    markdown = _repair_code_fences(markdown)

    def replace(match: re.Match[str]) -> str:
        hinted = match.group(1) or ""
        body = match.group(2)
        lang = _infer_fence_language(body, hinted)
        return f"```{lang}\n{body}```"

    return _FENCE_RE.sub(replace, markdown)
