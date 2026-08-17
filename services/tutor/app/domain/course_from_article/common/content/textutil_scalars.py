from __future__ import annotations

import re

from app.domain.course_from_article.common.content.constants import (
    _MAX_ARTICLE_FOR_PROMPT,
    _MAX_ARTICLE_FOR_PROMPT_COMPACT,
)


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
    if limit < 180:
        return text[:limit]
    head = max(60, int(limit * 0.40))
    mid = max(40, int(limit * 0.30))
    tail = max(40, limit - head - mid - 40)
    mid_start = max(0, (len(text) // 2) - (mid // 2))
    mid_chunk = text[mid_start : mid_start + mid]
    return f"{text[:head]}\n\n…\n\n{mid_chunk}\n\n…\n\n{text[-tail:]}"


def _combined_corpus(
    sources: list[dict[str, object]],
    *,
    compact: bool = False,
) -> str:
    if not sources:
        return ""
    budget = _MAX_ARTICLE_FOR_PROMPT_COMPACT if compact else _MAX_ARTICLE_FOR_PROMPT
    if len(sources) == 1:
        item = sources[0]
        body = _excerpt_balanced(str(item["content"]), budget - 80)
        return f"## Source 1: {item['title']}\n\n{body}"

    n = len(sources)
    headers = [f"## Source {i}: {item['title']}\n\n" for i, item in enumerate(sources, start=1)]
    overhead = sum(len(header) for header in headers) + 8 * n
    floor = 2_000 if compact else 3_600
    per = max(floor, (budget - overhead) // n)
    parts = [
        f"{header}{_excerpt_balanced(str(item['content']), per)}"
        for header, item in zip(headers, sources, strict=True)
    ]
    return "\n\n".join(parts)[:budget]
