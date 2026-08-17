from __future__ import annotations

import re
from typing import Literal

PracticeRuntime = Literal["python", "javascript", "shell", "sql", "go", "java", ""]

_FENCE = re.compile(r"```(\w+)", re.IGNORECASE)
_CLI_HINT = re.compile(
    r"(?:"
    r"\b[\w.-]+-cli\b|"
    r"^\s*\$\s+\S+|"
    r"\b(?:bash|sh|zsh|curl|wget)\b"
    r")",
    re.IGNORECASE | re.MULTILINE,
)
_PY_HINT = re.compile(
    r"(?:"
    r"\b(?:async\s+def |def |class |import |from \w+ import|pytest)\b"
    r"|\bprint\s*\("
    r")",
    re.MULTILINE,
)
_JS_HINT = re.compile(r"\b(?:const |let |require\(|npm |node )\b")
_SQL_HINT = re.compile(r"\b(?:SELECT |INSERT |CREATE TABLE)\b", re.IGNORECASE)


def detect_practice_runtime(source_text: str) -> PracticeRuntime:

    text = source_text or ""
    langs = [match.group(1).casefold() for match in _FENCE.finditer(text)]
    shell_langs = {"bash", "shell", "sh", "zsh", "console"}
    if any(lang in shell_langs for lang in langs) or _CLI_HINT.search(text):
        return "shell"
    if any(lang in {"python", "py"} for lang in langs) or _PY_HINT.search(text):
        return "python"
    if any(lang in {"sql"} for lang in langs) or _SQL_HINT.search(text):
        return "sql"
    if any(lang in {"go"} for lang in langs):
        return "go"
    if any(lang in {"java"} for lang in langs):
        return "java"
    if any(lang in {"javascript", "js", "typescript", "ts"} for lang in langs) or _JS_HINT.search(
        text
    ):
        return "javascript"
    return ""


def practice_template_looks_fake(template: str, *, source_text: str) -> bool:

    body = template or ""
    source = (source_text or "").casefold()
    for match in re.finditer(r"""(?:from\s+(\w+)|import\s+['\"]([^'\"]+)['\"])""", body):
        name = (match.group(1) or match.group(2) or "").split("/")[0].casefold()
        if not name or name in {"os", "sys", "re", "json", "typing", "pathlib", "collections"}:
            continue
        if name not in source and f"pip install {name}" not in source:
            return True
    for match in re.finditer(r"""require\(['\"]([^'\"]+)['\"]\)""", body):
        name = match.group(1).split("/")[0].casefold()
        if name.startswith("."):
            continue
        if name not in source and f"npm install {name}" not in source:
            return True
    return False
