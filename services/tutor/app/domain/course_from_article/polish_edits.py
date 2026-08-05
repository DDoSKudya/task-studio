from __future__ import annotations

from typing import Any

from .source_exercise_harvest import strip_theory_exercise_sections
from .textutil import _as_str


def _chapter_opening(content: str, limit: int) -> tuple[str, int]:
    text = content.strip()
    if not text:
        return "", 0
    if len(text) <= limit:
        return text, len(text)
    cut = text.rfind("\n\n", 0, limit)
    if cut < limit // 3:
        cut = limit
    return text[:cut].rstrip(), cut


def _polish_full_content_ok(original: str, revised: str) -> bool:
    text = revised.strip()
    if len(text) < 80:
        return False
    src = original.strip()
    if not src:
        return len(text) >= 80
    ratio = len(text) / max(1, len(src))

    upper = 3.5 if len(src) < 240 else 2.2
    return 0.45 <= ratio <= upper


def _apply_opening_edit(step: dict[str, object], opening: str, cut: int) -> bool:
    revised = opening.strip()
    if len(revised) < 28:
        return False
    original = str(step.get("content") or "")
    if cut <= 0:
        cut = min(len(original), max(len(revised), 200))

    if len(revised) > max(cut * 3, 400) + 200:
        return False
    rest = original[cut:].lstrip() if cut < len(original) else ""
    step["content"] = strip_theory_exercise_sections(f"{revised}\n\n{rest}" if rest else revised)
    return True


def _apply_book_polish_edits(
    theory_steps: list[dict[str, object]],
    payload: dict[str, Any],
    digests: list[dict[str, object]],
) -> int:
    edits_raw = payload.get("edits")
    if not isinstance(edits_raw, list):
        return 0
    by_id = {str(step.get("id") or ""): step for step in theory_steps}
    cut_by_id: dict[str, int] = {}
    for item in digests:
        sid = item.get("id")
        chars = item.get("opening_chars")
        if sid is None or not isinstance(chars, int):
            continue
        cut_by_id[str(sid)] = chars
    applied = 0
    for item in edits_raw:
        if not isinstance(item, dict):
            continue
        step_id = _as_str(item.get("id")) or ""
        step = by_id.get(step_id)
        if step is None:
            continue
        original = str(step.get("content") or "")
        full = _as_str(item.get("content"))
        if full and _polish_full_content_ok(original, full):
            step["content"] = strip_theory_exercise_sections(full.strip())
            applied += 1
            continue
        opening = _as_str(item.get("opening"))
        if not opening:
            continue
        cut = cut_by_id.get(step_id, 0)
        if _apply_opening_edit(step, opening, cut):
            applied += 1
    return applied
