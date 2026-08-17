from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.course_from_article.curriculum.outline.normalize_outline import (
    _titles_near_duplicate,
)
from app.domain.course_from_article.curriculum.theory.theory_sections import (
    split_sentences,
    split_source_units,
)
from app.domain.course_strategies import chapter_title_is_valid, sanitize_chapter_title

_HEADING_LINE = re.compile(r"^(#{1,3})\s+(\S.*?)\s*$", re.MULTILINE)
_MIN_UNIT_CHARS = 120
_LEADING_DISCOURSE = re.compile(
    r"^(?:сейчас|далее|затем|теперь|например|итак|here|now|next|then|for example)\s*[,—:-]?\s+",
    re.IGNORECASE,
)

_EXAMPLE_LABEL = re.compile(
    r"^(?:плохо|хорошо|неправильно|правильно|антипаттерн|было|стало"
    r"|bad|good|wrong|right|before|after)\b[\s—:,-]",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class TopicSeed:
    title: str
    objective: str
    excerpt: str
    source_title: str
    order: int
    from_heading: bool = False


def heading_of_unit(text: str) -> str:

    if match := _HEADING_LINE.search(text or ""):
        return sanitize_chapter_title(match.group(2).strip(), fallback="")
    first_line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    if first_line.startswith("#"):
        return sanitize_chapter_title(first_line.lstrip("# ").strip(), fallback="")
    words = first_line.split()
    if words and len(words) <= 8 and not first_line.rstrip().endswith((".", "!", "?")):
        return sanitize_chapter_title(first_line, fallback="")
    return ""


def title_from_unit(text: str) -> str:
    return heading_of_unit(text)


def section_heading(text: str, *, source_title: str = "") -> str:

    heading = heading_of_unit(text)
    if not heading or _EXAMPLE_LABEL.match(heading):
        return ""
    if source_title and _titles_near_duplicate(heading, source_title):
        return ""
    return heading


def title_from_claim(text: str, *, fallback: str) -> str:
    for sentence in split_sentences(text):
        claim = " ".join(sentence.split()).strip(" #*`>-")
        claim = _LEADING_DISCOURSE.sub("", claim)
        claim = claim[:1].upper() + claim[1:]
        if len(claim) < 24:
            continue
        words = claim.rstrip(".!?…").split()
        for count in range(min(8, len(words)), 2, -1):
            candidate = " ".join(words[:count]).strip(" ,;:—-")
            if chapter_title_is_valid(candidate):
                return candidate
    return sanitize_chapter_title(fallback, fallback="Основные понятия")


def objective_from_unit(text: str, *, title: str) -> str:
    sentences = split_sentences(text)
    if len(sentences) >= 2:
        return sentences[1][:400]
    if sentences:
        return sentences[0][:400]
    return title[:400]


def inventory_from_sources(
    sources: list[dict[str, object]],
    *,
    article: str = "",
    sentences_per_window: int,
) -> list[TopicSeed]:
    seeds: list[TopicSeed] = []
    order = 0
    for index, item in enumerate(sources, start=1):
        title = str(item.get("title") or f"Source {index}").strip() or f"Source {index}"
        content = str(item.get("content") or "").strip()
        if len(content) < _MIN_UNIT_CHARS:
            continue
        for unit in split_source_units(content, sentences_per_window=sentences_per_window):
            if len(unit.strip()) < _MIN_UNIT_CHARS:
                continue
            heading = section_heading(unit, source_title=title)
            seed_title = heading or title_from_claim(unit, fallback="Основные понятия")
            seeds.append(
                TopicSeed(
                    title=seed_title,
                    objective=objective_from_unit(unit, title=heading or title),
                    excerpt=unit.strip(),
                    source_title=title,
                    order=order,
                    from_heading=bool(heading),
                )
            )
            order += 1
    if seeds:
        return seeds

    for index, item in enumerate(sources, start=1):
        title = str(item.get("title") or f"Source {index}").strip() or f"Source {index}"
        content = str(item.get("content") or "").strip()
        if len(content) < _MIN_UNIT_CHARS:
            continue
        heading = section_heading(content, source_title=title)
        seed_title = heading or title_from_claim(content, fallback=title)
        seeds.append(
            TopicSeed(
                title=seed_title,
                objective=objective_from_unit(content, title=heading or title),
                excerpt=content,
                source_title=title,
                order=order,
                from_heading=bool(heading),
            )
        )
        order += 1
    if seeds:
        return seeds
    blob = (article or "").strip()
    if len(blob) < _MIN_UNIT_CHARS:
        return []
    heading = title_from_unit(blob)
    seed_title = heading or title_from_claim(blob, fallback="Article")
    return [
        TopicSeed(
            title=seed_title,
            objective=objective_from_unit(blob, title=heading or "Article"),
            excerpt=blob,
            source_title="Article",
            order=0,
            from_heading=bool(heading_of_unit(blob)),
        )
    ]
