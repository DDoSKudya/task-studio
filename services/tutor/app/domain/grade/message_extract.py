from __future__ import annotations

import re

_PAGE_KEYS = (
    "theory_md",
    "body_md",
    "markdown",
    "text",
    "html",
    "prompt",
    "description",
    "question",
    "statement",
)


def as_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def first_plain_str(*values: object) -> str:

    for value in values:
        if isinstance(value, str):
            return value
    return ""


def page_text(step: dict[str, object]) -> str:
    content = step.get("content")
    blobs: list[str] = []
    if isinstance(content, dict):
        for key in _PAGE_KEYS:
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                blobs.append(value.strip())
        for key in ("body", "prompt_html", "text_html"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                blobs.append(value.strip())
    elif isinstance(content, str) and content.strip():
        blobs.append(content.strip())
    for key in ("prompt", "description", "question"):
        value = step.get(key)
        if isinstance(value, str) and value.strip():
            blobs.append(value.strip())
    text = "\n\n".join(blobs)
    return text[:4500]


def starter_code(step: dict[str, object]) -> str:
    editor = step.get("editor")
    if isinstance(editor, dict):
        template = editor.get("template")
        if isinstance(template, str):
            return template
    template = step.get("template")
    return template if isinstance(template, str) else ""


def looks_like_sql(step: dict[str, object], submission: dict[str, object]) -> bool:
    runtime = step.get("runtime")
    if isinstance(runtime, str) and "sql" in runtime.lower():
        return True
    editor = step.get("editor")
    if isinstance(editor, dict):
        for key in ("runtime", "language"):
            value = editor.get(key)
            if isinstance(value, str) and "sql" in value.lower():
                return True
    source = submission.get("source")
    return isinstance(source, str) and bool(
        re.search(
            r"\b(select|insert|update|delete|from|join)\b",
            source,
            flags=re.IGNORECASE,
        )
    )
