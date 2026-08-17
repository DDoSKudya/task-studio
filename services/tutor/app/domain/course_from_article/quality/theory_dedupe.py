from __future__ import annotations

import re

_ORDINAL_PREFIX = re.compile(r"^\d{1,2}[\.\)\:]\s+")
_TITLE_NOISE = re.compile(r"[^\w\sа-яё-]", re.IGNORECASE)
_ID_PART_SUFFIX = re.compile(r"-\d+$")


def normalize_theory_title(title: str) -> str:
    cleaned = _ORDINAL_PREFIX.sub("", (title or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def title_dedupe_key(title: str) -> str:
    cleaned = normalize_theory_title(title).casefold()
    return _TITLE_NOISE.sub("", cleaned)


def _dedupe_scope_key(step: dict[str, object]) -> str:
    chapter = str(step.get("chapter_id") or "").strip()
    if chapter:
        return f"ch:{chapter}"
    raw_id = str(step.get("id") or "").strip()
    base = _ID_PART_SUFFIX.sub("", raw_id) if raw_id else ""
    return f"id:{base}" if base else "orphan"


def dedupe_theory_steps(steps: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    seen: dict[str, set[str]] = {}
    for step in steps:
        if str(step.get("kind") or "theory") != "theory":
            out.append(step)
            continue
        raw_title = str(step.get("title") or "")
        title = normalize_theory_title(raw_title) or raw_title.strip() or "Theory"
        key = title_dedupe_key(title)
        scope = _dedupe_scope_key(step)
        bucket = seen.setdefault(scope, set())
        if key and key in bucket:
            continue
        if key:
            bucket.add(key)
        payload = dict(step)
        payload["title"] = title
        out.append(payload)
    return out
