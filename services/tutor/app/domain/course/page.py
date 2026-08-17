from __future__ import annotations

import re
from html import unescape

from studio_contracts.api.session_schemas import StepContent

_PAGE_TEXT_KEYS = (
    "instructions",
    "description",
    "question",
    "text",
    "theory_md",
    "body_md",
    "prompt_md",
    "content",
)
PAGE_CONTENT_LIMIT = 3500
STARTER_CODE_LIMIT = 900


def strip_html(value: str) -> str:
    return unescape(re.sub(r"<[^>]+>", " ", value))


def step_page_text(step: StepContent) -> str:
    chunks: list[str] = []
    content = step.content
    seen: set[str] = set()
    for key in _PAGE_TEXT_KEYS:
        value = content.get(key)
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        chunks.append(normalized)
    body_html = content.get("body_html")
    if isinstance(body_html, str) and body_html.strip():
        plain = strip_html(body_html).strip()
        if plain and plain not in seen:
            chunks.append(plain)
    choices = content.get("choices")
    if isinstance(choices, list) and (
        labeled := [str(item).strip() for item in choices if str(item).strip()]
    ):
        chunks.append("Options: " + " | ".join(labeled[:8]))
    return re.sub(r"\s+", " ", "\n".join(chunks)).strip()


def starter_code(step: StepContent, *, limit: int = STARTER_CODE_LIMIT) -> str:
    if not step.editor:
        return ""
    template = step.editor.get("template")
    if not isinstance(template, str) or not template.strip():
        return ""
    text = template.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
