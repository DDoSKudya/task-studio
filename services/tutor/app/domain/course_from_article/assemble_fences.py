from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```([^\n`]*)\n([\s\S]*?)```", re.MULTILINE)

_FENCE_LINE_RE = re.compile(r"^\s*(`{2,})([A-Za-z][\w+-]*)?\s*$")

_PYTHON_START_RE = re.compile(
    r"^(?:"
    r"(?:async\s+)?def\s+\w+"
    r"|class\s+\w+"
    r"|from\s+\S+\s+import\b"
    r"|import\s+\S+"
    r"|@\w+"
    r")"
)
_PYTHON_CONTINUE_RE = re.compile(
    r"^(?:"
    r"[ \t]+\S"
    r"|#|"
    r"(?:else|elif|except|finally|try|with|for|while|if|return|raise|pass|yield|await)\b"
    r"|[\)\]\}]"
    r")"
)
_PROSE_LINE_RE = re.compile(
    r"^(?:"
    r"#{1,6}\s+\S"
    r"|[-*+]\s+\S"
    r"|\d+\.\s+\S"
    r"|>\s+\S"
    r")"
)


def _repair_code_fences(markdown: str) -> str:
    if not markdown or "`" not in markdown:
        return markdown

    lines = markdown.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    open_fence = False
    index = 0
    while index < len(lines):
        line = lines[index]
        match = _FENCE_LINE_RE.match(line.rstrip())
        if match:
            if not open_fence:
                lang = match.group(2) or ""
                if not lang:
                    peek = index + 1
                    while peek < len(lines) and not lines[peek].strip():
                        peek += 1
                    # Stray ``` after leaked code — drop instead of opening an empty fence.
                    if peek >= len(lines) or not _line_looks_like_python_code(
                        lines[peek], prev_was_code=False
                    ):
                        index += 1
                        continue
                out.append(f"```{lang}" if lang else "```")
                open_fence = True
            else:
                # LLM часто закрывает блок как ```text / ```bash вместо ```.
                out.append("```")
                open_fence = False
            index += 1
            continue
        out.append(line)
        index += 1

    if open_fence:
        out.append("```")
    return "\n".join(out)


def _line_looks_like_python_code(line: str, *, prev_was_code: bool) -> bool:
    stripped = line.rstrip()
    if not stripped:
        return False
    if stripped.startswith("```"):
        return False
    if _PROSE_LINE_RE.match(stripped):
        return False
    # Cyrillic-heavy prose sentence — not code.
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", stripped)
    cyr = sum("А" <= ch <= "я" or ch in "Ёё" for ch in letters)
    cyr_heavy = bool(letters) and cyr / len(letters) >= 0.45
    if (
        cyr_heavy
        and "def " not in stripped
        and "class " not in stripped
        and not stripped.startswith((" ", "\t"))
    ):
        return False
    if _PYTHON_START_RE.match(stripped):
        return True
    if prev_was_code and _PYTHON_CONTINUE_RE.match(stripped):
        return True
    # Premature fence close often leaves unindented methods still in the example.
    return bool(
        re.match(r"^def\s+(?:__)?\w+\s*\(", stripped) or re.match(r"^class\s+\w+", stripped)
    )


def _heal_orphaned_python_fences(markdown: str) -> str:
    """Merge Python that leaked after a premature ``` close back into the fence.

    Outside fences Markdown turns ``__set__`` into emphasis — the UI shows `set`.
    """
    if not markdown:
        return markdown
    lines = markdown.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    index = 0

    def absorb_leaked(body: list[str]) -> None:
        nonlocal index
        while index < len(lines):
            current = lines[index]
            if _FENCE_LINE_RE.match(current.rstrip()):
                peek = index + 1
                while peek < len(lines) and not lines[peek].strip():
                    peek += 1
                if peek < len(lines) and _line_looks_like_python_code(
                    lines[peek], prev_was_code=True
                ):
                    index += 1
                    continue
                break
            if _line_looks_like_python_code(current, prev_was_code=bool(body)):
                body.append(current)
                index += 1
                continue
            if not current.strip():
                peek = index + 1
                while peek < len(lines) and not lines[peek].strip():
                    peek += 1
                if peek < len(lines) and _line_looks_like_python_code(
                    lines[peek], prev_was_code=True
                ):
                    body.append(current)
                    index += 1
                    continue
            break

    while index < len(lines):
        line = lines[index]
        fence_match = _FENCE_LINE_RE.match(line.rstrip())
        if fence_match:
            lang = fence_match.group(2) or ""
            body: list[str] = []
            index += 1
            while index < len(lines) and not _FENCE_LINE_RE.match(lines[index].rstrip()):
                body.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            absorb_leaked(body)
            while body and not body[-1].strip():
                body.pop()
            joined = "\n".join(body)
            if not lang or lang.lower() in {"text", "plain", "plaintext"}:
                lang = _infer_fence_language(joined, lang)
            out.append(f"```{lang}" if lang else "```")
            out.extend(body)
            out.append("```")
            continue
        if _line_looks_like_python_code(line, prev_was_code=False):
            body = []
            absorb_leaked(body)
            while body and not body[-1].strip():
                body.pop()
            if body:
                joined = "\n".join(body)
                lang = _infer_fence_language(joined, "")
                out.append(f"```{lang}" if lang else "```")
                out.extend(body)
                out.append("```")
            continue
        out.append(line)
        index += 1
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
    markdown = _heal_orphaned_python_fences(_repair_code_fences(markdown))

    def replace(match: re.Match[str]) -> str:
        hinted = match.group(1) or ""
        body = match.group(2)
        lang = _infer_fence_language(body, hinted)
        return f"```{lang}\n{body}```"

    return _FENCE_RE.sub(replace, markdown)
