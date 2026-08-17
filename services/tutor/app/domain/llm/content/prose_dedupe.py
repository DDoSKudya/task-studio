from __future__ import annotations

import re

_THROAT_CLEARING_LINE = re.compile(
    r"^(?:#{1,3}\s+)?("
    r"(?:в\s+(?:этой|данной)\s+главе[^.!?]{0,160}[.!?])|"
    r"(?:in\s+this\s+chapter[^.!?]{0,160}[.!?])|"
    r"(?:it\s+is\s+important\s+to\s+note[^.!?]{0,120}[.!?])|"
    r"(?:важно\s+(?:отметить|понимать|запомнить)[^.!?]{0,120}[.!?])|"
    r"(?:давайте\s+(?:рассмотрим|разберём|изучим)[^.!?]{0,120}[.!?])|"
    r"(?:we\s+will\s+(?:explore|discuss|learn)[^.!?]{0,120}[.!?])"
    r")\s*$",
    re.IGNORECASE,
)
_NAVIGATION_SENTENCE = re.compile(
    r"^(?:"
    r"(?:в\s+следующем\s+разделе|далее|теперь\s+(?:давайте\s+)?перейд[её]м|"
    r"переходим\s+к\s+следующему\s+(?:шагу|разделу))[^.!?]{0,220}[.!?]|"
    r"(?:in\s+the\s+next\s+section|next,\s+we(?:'ll|\s+will)|"
    r"now\s+let(?:'s|\s+us)\s+move\s+on)[^.!?]{0,220}[.!?]"
    r")$",
    re.IGNORECASE,
)
_NAVIGATION_HEADING = re.compile(
    r"^(?:"
    r"переход\s+к\s+следующ\w*|"
    r"далее\s*[-—:.]|"
    r"next\s+section|"
    r"transition\s+to\s+(?:the\s+)?next"
    r")",
    re.IGNORECASE,
)
_PROSE_WORD = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
_FENCE_BLOCK = re.compile(r"```([^\n`]*)\n([\s\S]*?)(?:```|$)", re.IGNORECASE)
_CODE_FENCE_LANGS = frozenset(
    {
        "python",
        "py",
        "bash",
        "sh",
        "shell",
        "zsh",
        "javascript",
        "js",
        "typescript",
        "ts",
        "go",
        "java",
        "rust",
        "sql",
        "c",
        "cpp",
        "c++",
        "csharp",
        "cs",
        "ruby",
        "php",
        "kotlin",
        "swift",
        "r",
        "powershell",
        "ps1",
        "dockerfile",
        "yaml",
        "yml",
        "json",
        "html",
        "css",
        "toml",
        "ini",
        "text",
        "plaintext",
        "console",
        "output",
    }
)
_CODEISH_LINE = re.compile(
    r"^\s*(?:"
    r">>> |\.\.\. |"
    r"(?:from\s+\S+\s+import\s+|import\s+[A-Za-z_]|def\s+|class\s+|async\s+def\s+)|"
    r"print\s*\(|"
    r"[A-Za-z_][\w.]*\s*=\s*"
    r")"
)
_MERMAID_HEAD = re.compile(
    r"^\s*(?:flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|mindmap)\b",
    re.IGNORECASE,
)
_MD_LINK = re.compile(r"\[[^\]]+\]\([^)]+\)")


def strip_throat_clearing(text: str, *, max_passes: int = 4) -> str:

    body = (text or "").strip()
    if not body:
        return body
    paragraphs = re.split(r"\n\s*\n+", body)
    for _ in range(max_passes):
        if not paragraphs:
            break
        head = paragraphs[0].strip()
        if not head or not _THROAT_CLEARING_LINE.match(head):
            break
        paragraphs.pop(0)
    return "\n\n".join(paragraphs).strip()


def collapse_repeated_prose(text: str, *, min_block: int = 240) -> str:

    body = (text or "").strip()
    if len(body) < min_block * 2:
        return body

    max_period = min(len(body) // 2, 3_200)
    for period in range(min_block, max_period + 1):
        if body[:period] == body[period : period * 2]:
            return body[:period].rstrip()

    for size in range(min(max_period, 1_200), min_block, -20):
        needle = body[:size]
        hit = body.find(needle, size)
        if hit != -1:
            return body[:hit].rstrip()

    return _collapse_ngram_run(body, window=min(200, min_block))


_HEADING_LINE = re.compile(r"^(#{1,3})\s+(\S.*?)\s*$")


def collapse_repeated_sections(text: str) -> str:

    body = (text or "").strip()
    if not body:
        return body
    sections = _sections_by_heading(body)
    if len(sections) <= 1:
        return body

    kept: list[tuple[str | None, str]] = []
    seen_titles: set[str] = set()
    for title, block in sections:
        if title is None:
            kept.append((title, block))
            continue
        key = _normalize_section_title(title)
        if key in seen_titles:
            continue
        seen_titles.add(key)
        kept.append((title, block))
    return _join_sections(kept)


def collapse_heading_cycle(text: str) -> str:

    body = (text or "").strip()
    if not body:
        return body
    sections = _sections_by_heading(body)
    titled = [(title, block) for title, block in sections if title]
    if len(titled) < 4:
        return body
    keys = [_normalize_section_title(title or "") for title, _ in titled]
    period = _detect_key_cycle(keys)
    if period is None:
        return body
    kept: list[tuple[str | None, str]] = []
    titled_kept = 0
    seen_heading = False
    for title, block in sections:
        if title is None:
            if not seen_heading:
                kept.append((title, block))
            continue
        seen_heading = True
        if titled_kept >= period:
            continue
        kept.append((title, block))
        titled_kept += 1
    return _join_sections(kept) if kept else body


def _detect_key_cycle(keys: list[str]) -> int | None:
    total = len(keys)
    for period in range(1, min(4, total // 2) + 1):
        if total < period * 2:
            continue
        chunk = keys[:period]
        if not all(chunk):
            continue
        repeats = 0
        index = 0
        while index + period <= total and keys[index : index + period] == chunk:
            repeats += 1
            index += period
        if repeats >= 2 and index >= period * 2:
            return period
    return None


def collapse_similar_paragraphs(text: str, *, prefix_words: int = 4) -> str:
    body = (text or "").strip()
    if not body:
        return body
    paragraphs = re.split(r"\n\s*\n+", body)
    kept: list[str] = []
    prev_stem: str | None = None
    word_limit = max(3, prefix_words)
    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if not stripped:
            continue
        if stripped.startswith("```") or _HEADING_LINE.match(stripped.split("\n", 1)[0]):
            kept.append(stripped)
            prev_stem = None
            continue
        plain = re.sub(r"\s+", " ", stripped.casefold())
        words = plain.split()
        if len(words) < word_limit:
            kept.append(stripped)
            prev_stem = None
            continue
        stem = " ".join(words[:word_limit])
        if prev_stem is not None and stem == prev_stem:
            continue
        prev_stem = stem
        kept.append(stripped)
    return "\n\n".join(kept).strip()


def strip_navigation_sentences(text: str) -> str:

    paragraphs = re.split(r"\n\s*\n+", (text or "").strip())
    kept: list[str] = []
    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if not stripped:
            continue
        first_line = stripped.split("\n", 1)[0]
        heading = _HEADING_LINE.match(first_line)
        if heading and _NAVIGATION_HEADING.match(heading.group(2).strip()):
            continue
        if "```" in stripped or heading:
            kept.append(stripped)
            continue
        sentences = [
            cleaned
            for sentence in _SENTENCE_SPLIT.split(stripped)
            if (cleaned := sentence.strip()) and not _NAVIGATION_SENTENCE.match(cleaned)
        ]
        if sentences:
            kept.append(" ".join(sentences))
    return "\n\n".join(kept).strip()


def collapse_near_duplicate_paragraphs(
    text: str,
    *,
    overlap: float = 0.6,
    min_chars: int = 80,
) -> str:

    paragraphs = re.split(r"\n\s*\n+", (text or "").strip())
    kept: list[str] = []
    seen_terms: list[frozenset[str]] = []
    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if not stripped:
            continue
        if "```" in stripped or _HEADING_LINE.match(stripped.split("\n", 1)[0]):
            kept.append(stripped)
            continue
        terms = frozenset(
            word.casefold() for word in _PROSE_WORD.findall(stripped) if len(word) >= 4
        )
        is_repeat = (
            len(stripped) >= min_chars
            and len(terms) >= 8
            and any(
                len(terms & prior) / min(len(terms), len(prior)) >= overlap
                for prior in seen_terms
                if prior
            )
        )
        if is_repeat:
            continue
        kept.append(stripped)
        if len(stripped) >= min_chars and len(terms) >= 8:
            seen_terms.append(terms)
    return "\n\n".join(kept).strip()


def strip_resource_link_lists(text: str) -> str:
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n+", (text or "").strip()):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("```") or _HEADING_LINE.match(stripped.split("\n", 1)[0]):
            paragraphs.append(stripped)
            continue
        links = _MD_LINK.findall(stripped)
        if not links:
            paragraphs.append(stripped)
            continue
        remnant = _MD_LINK.sub(" ", stripped)
        remnant = re.sub(r"^[\s\-*\d.)]+", "", remnant)
        remnant = re.sub(r"\s+", " ", remnant).strip(" -:;—")
        letters = [ch for ch in remnant if ch.isalpha()]
        if len(links) >= 1 and len(letters) < 48:
            continue
        if len(links) >= 2 and len("".join(links)) / max(1, len(stripped)) >= 0.55:
            continue
        paragraphs.append(stripped)
    return "\n\n".join(paragraphs).strip()


def strip_leaked_code_blobs(text: str) -> str:
    """Убирает fence прикладного кода и абзацы-«сырой код»; mermaid сохраняет."""

    def _replace_fence(match: re.Match[str]) -> str:
        lang = (match.group(1) or "").strip().split()[0].casefold() if match.group(1) else ""
        body = match.group(2) or ""
        if lang == "mermaid" or _MERMAID_HEAD.match(body):
            return f"```mermaid\n{body.rstrip()}\n```"
        if lang in _CODE_FENCE_LANGS or lang == "":
            # Пустой lang часто = обрубок листинга из статьи; diagram-like оставляем.
            if lang == "" and _MERMAID_HEAD.match(body):
                return f"```mermaid\n{body.rstrip()}\n```"
            return ""
        return match.group(0)

    body = _FENCE_BLOCK.sub(_replace_fence, text or "")
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n+", body):
        stripped = block.strip()
        if not stripped:
            continue
        if stripped.startswith("```"):
            paragraphs.append(stripped)
            continue
        lines = [line for line in stripped.splitlines() if line.strip()]
        if not lines:
            continue
        codeish = sum(1 for line in lines if _CODEISH_LINE.match(line))
        if len(lines) >= 2 and codeish / len(lines) >= 0.6:
            continue
        if len(lines) == 1 and _CODEISH_LINE.match(lines[0]) and len(lines[0]) < 120:
            continue
        paragraphs.append(stripped)
    return "\n\n".join(paragraphs).strip()


def clean_theory_markdown(text: str) -> str:
    cleaned = strip_leaked_code_blobs(text)
    cleaned = strip_resource_link_lists(cleaned)
    cleaned = collapse_repeated_prose(cleaned)
    cleaned = collapse_heading_cycle(cleaned)
    cleaned = collapse_repeated_sections(cleaned)
    cleaned = collapse_similar_paragraphs(cleaned)
    cleaned = strip_navigation_sentences(cleaned)
    cleaned = collapse_near_duplicate_paragraphs(cleaned)
    cleaned = strip_throat_clearing(cleaned)
    try:
        from app.domain.ollama.quality_lang import repair_script_mixing
    except ImportError:
        return cleaned
    return repair_script_mixing(cleaned)


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")


def sentence_fingerprint(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().casefold())


def drop_seen_sentences(
    text: str,
    seen: set[str],
    *,
    min_chars: int = 40,
) -> str:

    body = (text or "").strip()
    if not body:
        return body
    paragraphs = re.split(r"\n\s*\n+", body)
    kept_paragraphs: list[str] = []
    for paragraph in paragraphs:
        stripped = paragraph.strip()
        if not stripped:
            continue
        first_line = stripped.split("\n", 1)[0]
        if stripped.startswith("```") or _HEADING_LINE.match(first_line):
            kept_paragraphs.append(stripped)
            continue
        kept_sentences: list[str] = []
        for sentence in _SENTENCE_SPLIT.split(stripped):
            plain = " ".join(sentence.split()).strip()
            if not plain:
                continue
            key = sentence_fingerprint(plain)
            if len(plain) >= min_chars:
                if key in seen:
                    continue
                seen.add(key)
            kept_sentences.append(plain)
        if kept_sentences:
            kept_paragraphs.append(" ".join(kept_sentences))
    return "\n\n".join(kept_paragraphs).strip()


def dedupe_theory_steps_across_course(steps: list[dict[str, object]]) -> int:

    seen: set[str] = set()
    touched = 0
    for step in steps:
        if str(step.get("kind") or "theory") != "theory":
            continue
        before = str(step.get("content") or "")
        after = drop_seen_sentences(before, seen)
        if after and after != before:
            step["content"] = after
            touched += 1
        elif before and not after:
            continue
    return touched


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
        match = None if in_fence else _HEADING_LINE.match(line)
        if match:
            flush()
            title = match.group(2).strip()
            buf = [line]
            continue
        buf.append(line)
    flush()
    return sections


def _normalize_section_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", (title or "").strip().casefold())
    cleaned = re.sub(r"[^\w\sа-яё-]", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def _join_sections(sections: list[tuple[str | None, str]]) -> str:
    if not sections:
        return ""
    return "\n\n".join(block.strip() for _, block in sections if block.strip()).strip()


def continuation_is_restart(assembled: str, chunk: str) -> bool:
    head = (assembled or "").strip()
    piece = (chunk or "").strip()
    if len(head) < 80 or len(piece) < 80:
        return False
    probe = head[: min(160, len(head))]
    return piece.startswith(probe[:100])


def _collapse_ngram_run(text: str, *, window: int) -> str:
    if len(text) < window * 4:
        return text
    step = max(24, window // 5)
    positions: dict[str, list[int]] = {}
    for index in range(0, len(text) - window + 1, step):
        gram = text[index : index + window]
        bucket = positions.setdefault(gram, [])
        bucket.append(index)
        if len(bucket) >= 3 and bucket[0] < len(text) // 2:
            return text[: bucket[1]].rstrip()
    return text
