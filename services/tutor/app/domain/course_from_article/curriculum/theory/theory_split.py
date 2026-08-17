from __future__ import annotations

import re

from app.domain.course_from_article.quality.theory_dedupe import (
    dedupe_theory_steps,
    normalize_theory_title,
)

_HEADING_RE = re.compile(r"^(#{1,3})\s+(\S.*?)\s*$")
_DEFAULT_MAX_CHARS = 3000
_DEFAULT_MAX_PARTS = 3
_GENERIC_PART_TITLES = frozenset(
    {
        "заключение",
        "conclusion",
        "summary",
        "recap",
        "итоги",
        "выводы",
        "краткое повторение",
        "closing",
        "wrap-up",
        "переход к следующему разделу",
        "переход к следующей главе",
        "next section",
    }
)
_NAV_PART_TITLE = re.compile(
    r"^(?:переход\s+к\s+следующ\w*|далее\s*[-—:.]|next\s+section|"
    r"transition\s+to\s+(?:the\s+)?next)",
    re.IGNORECASE,
)


def split_long_theory_steps(
    steps: list[dict[str, object]],
    *,
    enabled: bool = True,
    max_chars: int = _DEFAULT_MAX_CHARS,
    max_parts: int = _DEFAULT_MAX_PARTS,
) -> list[dict[str, object]]:
    if not enabled or max_chars < 400:
        return list(steps)
    part_limit = max(1, max_parts)
    out: list[dict[str, object]] = []
    for step in steps:
        content = str(step.get("content") or "").strip()
        if len(content) <= max_chars:
            out.append(step)
            continue
        parts = _split_markdown_parts(content, max_chars=max_chars)
        parts = _merge_parts_to_limit(parts, max_parts=part_limit)
        parts = _absorb_thin_parts(parts, min_chars=420)
        if len(parts) <= 1:
            if parts:
                step = {**step, "content": parts[0][1]}
            out.append(step)
            continue
        base_id = str(step.get("id") or "theory")
        base_title = str(step.get("title") or "Theory")
        chapter_id = step.get("chapter_id")
        step_images = step.get("images")
        image_urls = (
            [
                url
                for url in step_images
                if isinstance(url, str) and url.startswith(("http://", "https://"))
            ]
            if isinstance(step_images, list)
            else []
        )
        for index, (part_title, part_body) in enumerate(parts, start=1):
            payload = {
                key: value
                for key, value in step.items()
                if key not in {"id", "title", "content", "images"}
            }
            payload["id"] = base_id if index == 1 else f"{base_id}-{index}"
            payload["kind"] = "theory"
            payload["title"] = _part_display_title(
                part_title,
                base_title=base_title,
                index=index,
            )
            payload["content"] = part_body
            if part_images := [url for url in image_urls if url in part_body]:
                payload["images"] = part_images
            if chapter_id is not None:
                payload["chapter_id"] = chapter_id
            out.append(payload)
    return dedupe_theory_steps(out)


def _absorb_thin_parts(
    parts: list[tuple[str, str]],
    *,
    min_chars: int = 420,
) -> list[tuple[str, str]]:
    if len(parts) <= 1:
        return parts
    merged = list(parts)
    changed = True
    while changed and len(merged) > 1:
        changed = False
        for index in range(len(merged) - 1, 0, -1):
            title, body = merged[index]
            if _part_has_enough_prose(body, min_chars=min_chars):
                continue
            left_title, left_body = merged[index - 1]
            merged = [
                *merged[: index - 1],
                (left_title or title, f"{left_body}\n\n{body}".strip()),
                *merged[index + 1 :],
            ]
            changed = True
            break
        if changed or len(merged) < 2:
            continue
        title, body = merged[0]
        if _part_has_enough_prose(body, min_chars=min_chars):
            continue
        right_title, right_body = merged[1]
        merged = [
            (right_title or title, f"{body}\n\n{right_body}".strip()),
            *merged[2:],
        ]
        changed = True
    return merged


_WRAPUP_STUB = re.compile(
    r"^(?:теперь\s+(?:ты|вы)\s+знае(?:шь|те)|итог|в\s+итоге|подвед[её]м\s+итог|"
    r"in\s+summary|to\s+sum\s+up|you\s+now\s+know)\b",
    re.IGNORECASE,
)


def _heading_free_prose(body: str) -> str:
    lines = [line for line in (body or "").splitlines() if not _HEADING_RE.match(line.strip())]
    return "\n".join(lines).strip()


def _part_has_enough_prose(body: str, *, min_chars: int) -> bool:
    prose = _heading_free_prose(body)
    if _looks_like_wrapup_stub(prose or body):
        return False
    return len(prose) >= min_chars


def _looks_like_wrapup_stub(body: str) -> bool:
    text = " ".join((body or "").split())
    if len(text) >= 900:
        return False
    return bool(_WRAPUP_STUB.search(text))


def _merge_parts_to_limit(
    parts: list[tuple[str, str]],
    *,
    max_parts: int,
) -> list[tuple[str, str]]:
    if len(parts) <= max_parts:
        return parts
    merged = list(parts)
    while len(merged) > max_parts:
        best_index = 0
        best_size: int | None = None
        for index in range(len(merged) - 1):
            size = len(merged[index][1]) + len(merged[index + 1][1])
            if best_size is None or size < best_size:
                best_size = size
                best_index = index
        left_title, left_body = merged[best_index]
        right_title, right_body = merged[best_index + 1]
        title = left_title or right_title
        body = f"{left_body}\n\n{right_body}".strip()
        merged = [
            *merged[:best_index],
            (title, body),
            *merged[best_index + 2 :],
        ]
    return merged


def _split_markdown_parts(content: str, *, max_chars: int) -> list[tuple[str, str]]:
    sections = _sections_by_heading(content)
    if len(sections) <= 1:
        return _split_oversized_block(content, max_chars=max_chars)

    buckets: list[tuple[str, list[str]]] = []
    for heading, body in sections:
        title = heading or ""
        if not buckets:
            buckets.append((title, [body]))
            continue
        current_title, parts = buckets[-1]
        candidate = "\n\n".join([*parts, body])
        if len(candidate) <= max_chars:
            parts.append(body)
            if not current_title and title:
                buckets[-1] = (title, parts)
            continue
        buckets.append((title, [body]))

    return [(title or "", "\n\n".join(parts).strip()) for title, parts in buckets if parts]


def _sections_by_heading(content: str) -> list[tuple[str | None, str]]:
    lines = content.replace("\r\n", "\n").split("\n")
    sections: list[tuple[str | None, str]] = []
    buf: list[str] = []
    title: str | None = None
    in_fence = False

    def flush() -> None:
        nonlocal buf, title
        text = "\n".join(buf).strip()
        if text:
            sections.append((title, text))
        buf = []
        title = None

    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            buf.append(line)
            continue
        match = None if in_fence else _HEADING_RE.match(line)
        if match:
            flush()
            title = match.group(2).strip()
            buf = [line]
            continue
        buf.append(line)
    flush()
    return sections


def _split_oversized_block(content: str, *, max_chars: int) -> list[tuple[str, str]]:
    chunks = _split_outside_fences(content, max_chars=max_chars)
    if len(chunks) <= 1:
        return [("", content)]
    return [("", chunk) for chunk in chunks]


def _split_outside_fences(content: str, *, max_chars: int) -> list[str]:
    lines = content.replace("\r\n", "\n").split("\n")
    blocks: list[str] = []
    buf: list[str] = []
    in_fence = False
    size = 0

    def flush() -> None:
        nonlocal buf, size
        text = "\n".join(buf).strip()
        if text:
            blocks.append(text)
        buf = []
        size = 0

    for line in lines:
        fence = line.strip().startswith("```")
        addition = len(line) + 1
        if not in_fence and not fence and buf and size + addition > max_chars and not line.strip():
            flush()
            continue
        if fence:
            in_fence = not in_fence
        buf.append(line)
        size += addition
        if not in_fence and size >= max_chars and not line.strip():
            flush()
    flush()
    return blocks or [content]


def _part_display_title(part_title: str, *, base_title: str, index: int) -> str:
    heading = normalize_theory_title(part_title or "")
    base = normalize_theory_title(base_title) or base_title.strip()
    if heading and _NAV_PART_TITLE.match(heading.strip()):
        heading = ""
    if not heading:
        return base if index == 1 else f"{base} ({index})"
    normalized = heading.casefold()
    base_norm = base.casefold()
    if normalized in _GENERIC_PART_TITLES or normalized == base_norm:
        return base if index == 1 else f"{base} ({index})"
    return heading
