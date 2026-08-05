from __future__ import annotations

import re

_HEADING_RE = re.compile(r"^(#{1,3})\s+(\S.*?)\s*$")
_DEFAULT_MAX_CHARS = 3000
_DEFAULT_MAX_PARTS = 6


def split_long_theory_steps(
    steps: list[dict[str, object]],
    *,
    enabled: bool = True,
    max_chars: int = _DEFAULT_MAX_CHARS,
    max_parts: int = _DEFAULT_MAX_PARTS,
) -> list[dict[str, object]]:
    if not enabled or max_chars < 400:
        return steps
    part_limit = max(1, max_parts)
    out: list[dict[str, object]] = []
    for step in steps:
        content = str(step.get("content") or "").strip()
        if len(content) <= max_chars:
            out.append(step)
            continue
        parts = _split_markdown_parts(content, max_chars=max_chars)
        parts = _merge_parts_to_limit(parts, max_parts=part_limit)
        if len(parts) <= 1:
            out.append(step)
            continue
        base_id = str(step.get("id") or "theory")
        base_title = str(step.get("title") or "Theory")
        chapter_id = step.get("chapter_id")
        for index, (part_title, part_body) in enumerate(parts, start=1):
            payload = {
                key: value for key, value in step.items() if key not in {"id", "title", "content"}
            }
            payload["id"] = base_id if index == 1 else f"{base_id}-{index}"
            payload["kind"] = "theory"
            payload["title"] = part_title or (
                base_title if index == 1 else f"{base_title} ({index})"
            )
            payload["content"] = part_body
            if chapter_id is not None:
                payload["chapter_id"] = chapter_id
            out.append(payload)
    return out


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
