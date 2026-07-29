from __future__ import annotations

import re

from .constants import _MAX_ARTICLE_FOR_PROMPT


def _as_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _slug(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:64] or "item"


def _string_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()][:12]


def _join_string_list(raw: object, *, limit: int = 8) -> str:
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if not isinstance(raw, list):
        return ""
    bits = [str(item).strip() for item in raw if str(item).strip()]
    return "; ".join(bits[:limit])


def _excerpt_balanced(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit < 120:
        return text[:limit]
    head = int(limit * 0.55)
    tail = max(40, limit - head - 20)
    return f"{text[:head]}\n\n…\n\n{text[-tail:]}"


def _combined_corpus(sources: list[dict[str, object]]) -> str:
                                                                                        
    if not sources:
        return ""
    if len(sources) == 1:
        item = sources[0]
        body = _excerpt_balanced(str(item["content"]), _MAX_ARTICLE_FOR_PROMPT - 80)
        return f"## Source 1: {item['title']}\n\n{body}"

    n = len(sources)
    headers = [f"## Source {i}: {item['title']}\n\n" for i, item in enumerate(sources, start=1)]
    overhead = sum(len(header) for header in headers) + 8 * n
    per = max(2_400, (_MAX_ARTICLE_FOR_PROMPT - overhead) // n)
    parts = [
        f"{header}{_excerpt_balanced(str(item['content']), per)}"
        for header, item in zip(headers, sources, strict=True)
    ]
    return "\n\n".join(parts)[:_MAX_ARTICLE_FOR_PROMPT]
