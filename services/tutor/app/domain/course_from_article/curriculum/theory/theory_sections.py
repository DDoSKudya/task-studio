from __future__ import annotations

import re

from app.domain.llm.content.prose_dedupe import clean_theory_markdown

_HEADING_SPLIT_RE = re.compile(r"(?m)^(#{1,3}\s+\S.*?)$")
_SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+")

_TARGET_SECTION_CHARS = 1_100
_MIN_PARAGRAPH_PACK = 400
_MAX_SECTION_PARTS = 6
_MAX_SENTENCE_WINDOWS = 10_000
_WINDOW_OVERLAP = 1


def split_theory_excerpt(
    excerpt: str,
    *,
    target_chars: int = _TARGET_SECTION_CHARS,
) -> list[str]:
    text = (excerpt or "").strip()
    if not text:
        return []
    by_heading = _split_on_markdown_headings(text)
    if len(by_heading) >= 2:
        parts = _merge_small_chunks(by_heading, target_chars=target_chars)
    else:
        parts = _pack_paragraphs(text, target_chars=target_chars)
    return _cap_section_parts(parts, max_parts=_MAX_SECTION_PARTS)


def _cap_section_parts(parts: list[str], *, max_parts: int) -> list[str]:
    if len(parts) <= max_parts:
        return parts
    capped: list[str] = []
    start = 0
    total = len(parts)
    for bucket_index in range(max_parts):
        remaining_buckets = max_parts - bucket_index
        remaining_parts = total - start
        take = max(1, (remaining_parts + remaining_buckets - 1) // remaining_buckets)
        capped.append("\n\n".join(parts[start : start + take]))
        start += take
        if start >= total:
            break
    return capped


def split_sentences(text: str) -> list[str]:
    blob = " ".join((text or "").split())
    if not blob:
        return []
    parts = [part.strip() for part in _SENTENCE_RE.split(blob) if part.strip()]
    return parts or [blob]


def adaptive_window_size(
    sentence_count: int,
    *,
    preferred: int,
    max_windows: int = _MAX_SENTENCE_WINDOWS,
) -> int:
    preferred = max(1, preferred)
    if sentence_count <= preferred:
        return max(1, sentence_count)
    if max_windows < 1:
        return sentence_count
    needed = (sentence_count + preferred - 1) // preferred
    if needed <= max_windows:
        return preferred
    return max(preferred, (sentence_count + max_windows - 1) // max_windows)


def split_source_units(
    text: str,
    *,
    sentences_per_window: int = 3,
    max_windows: int = 80,
) -> list[str]:

    blob = (text or "").strip()
    if not blob:
        return []
    headed = _split_on_markdown_headings(blob)
    if len(headed) >= 2:
        return [part.strip() for part in headed if part.strip()]
    windows = pack_sentence_windows(
        blob,
        sentences_per_window=sentences_per_window,
        max_windows=max_windows,
    )
    return windows or [blob]


def pack_sentence_windows(
    text: str,
    *,
    sentences_per_window: int = 3,
    overlap: int = _WINDOW_OVERLAP,
    max_windows: int = _MAX_SENTENCE_WINDOWS,
) -> list[str]:

    sentences = split_sentences(text)
    if not sentences:
        return []
    size = adaptive_window_size(
        len(sentences),
        preferred=sentences_per_window,
        max_windows=max_windows,
    )
    step = max(1, size - min(max(0, overlap), size - 1))
    windows: list[str] = []
    start = 0
    while start < len(sentences):
        end = min(len(sentences), start + size)
        windows.append(" ".join(sentences[start:end]))
        if end >= len(sentences):
            break
        start += step
    return windows


def align_section_cache(cached: list[str], section_count: int) -> list[str]:

    if section_count < 1:
        return []
    if len(cached) > section_count:
        return []
    missing = section_count - len(cached)
    if missing:
        return [*cached, *([""] * missing)]
    return cached


def stitch_theory_sections(parts: list[str]) -> str:
    blocks = [part.strip() for part in parts if part.strip()]
    if not blocks:
        return ""
    return clean_theory_markdown("\n\n".join(blocks))


def theory_chapter_digest(content: str, *, max_chars: int = 420) -> str:
    prose = clean_theory_markdown(content or "").strip()
    if not prose:
        return ""
    lines = [
        line.strip()
        for line in prose.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    blob = " ".join(lines)
    sentences = [part.strip() for part in _SENTENCE_RE.split(blob) if part.strip()]
    if not sentences:
        return blob[:max_chars].rstrip()
    digest = " ".join(sentences[:4])
    if len(digest) > max_chars:
        digest = digest[: max_chars - 1].rstrip() + "…"
    return digest


def _split_on_markdown_headings(text: str) -> list[str]:
    parts = _HEADING_SPLIT_RE.split(text)
    if len(parts) < 3:
        return [text]
    chunks: list[str] = []
    preamble = parts[0].strip()
    if preamble:
        chunks.append(preamble)
    index = 1
    while index + 1 < len(parts):
        heading = parts[index].strip()
        body = parts[index + 1].strip()
        chunk = f"{heading}\n\n{body}".strip() if body else heading
        if chunk:
            chunks.append(chunk)
        index += 2
    return chunks or [text]


def _pack_paragraphs(text: str, *, target_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        return [text]
    if len(text) <= target_chars:
        return [text]
    packs: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in paragraphs:
        extra = len(paragraph) + (2 if current else 0)
        if current and size + extra > target_chars and size >= _MIN_PARAGRAPH_PACK:
            packs.append("\n\n".join(current))
            current = [paragraph]
            size = len(paragraph)
            continue
        current.append(paragraph)
        size += extra
    if current:
        packs.append("\n\n".join(current))
    return packs or [text]


def _merge_small_chunks(chunks: list[str], *, target_chars: int) -> list[str]:
    if len(chunks) <= 1:
        return chunks
    merged: list[str] = []
    bucket = chunks[0]
    for chunk in chunks[1:]:
        both_headed = bucket.lstrip().startswith("#") and chunk.lstrip().startswith("#")
        if both_headed and len(bucket) >= _MIN_PARAGRAPH_PACK:
            merged.append(bucket)
            bucket = chunk
            continue
        if len(bucket) < _MIN_PARAGRAPH_PACK and len(bucket) + len(chunk) + 2 <= target_chars * 2:
            bucket = f"{bucket}\n\n{chunk}"
            continue
        if len(bucket) + len(chunk) + 2 <= target_chars:
            bucket = f"{bucket}\n\n{chunk}"
            continue
        merged.append(bucket)
        bucket = chunk
    merged.append(bucket)
    return merged
