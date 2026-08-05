from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_MIN_EXCERPT = 24
_MAX_EXCERPTS = 40
_MAX_REMOVE_RATIO = 0.45


def _as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if text := str(item or "").strip():
            out.append(text)
    return out


def parse_dechrome_plan(parsed: dict[str, object]) -> tuple[str, list[str]]:
    title = str(parsed.get("title") or "").strip()
    excerpts = _as_str_list(parsed.get("remove_excerpts"))
    return title, excerpts


def apply_dechrome(
    markdown: str,
    *,
    remove_excerpts: list[str],
    title_hint: str = "",
) -> tuple[str, int]:
    """Удаляет только точные вхождения, помеченные анализом. Возвращает (md, removed_chars)."""
    body = markdown
    removed = 0
    seen: set[str] = set()
    for raw in remove_excerpts[:_MAX_EXCERPTS]:
        excerpt = raw.strip()
        if len(excerpt) < _MIN_EXCERPT or excerpt in seen:
            continue
        if excerpt not in body:
            continue
        seen.add(excerpt)
        count = body.count(excerpt)
        # Не вырезаем одно и то же слишком часто — защита от коротких «универсальных» кусков.
        if count > 8:
            logger.info("article dechrome: skip over-common excerpt (%s hits)", count)
            continue
        body = body.replace(excerpt, "")
        removed += len(excerpt) * count

    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if title_hint and not body.lstrip().startswith("#"):
        body = f"# {title_hint.strip()}\n\n{body}"

    if not body or removed > int(len(markdown) * _MAX_REMOVE_RATIO):
        logger.warning(
            "article dechrome: rejected (removed=%s of %s)",
            removed,
            len(markdown),
        )
        return markdown, 0
    return body, removed
