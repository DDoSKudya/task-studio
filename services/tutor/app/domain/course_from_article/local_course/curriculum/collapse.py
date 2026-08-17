from __future__ import annotations

import re
from dataclasses import replace

from app.domain.course_from_article.curriculum.outline.normalize_outline import (
    topics_are_duplicates,
)
from app.domain.course_from_article.curriculum.theory.theory_sections import (
    split_sentences,
    split_source_units,
)
from app.domain.course_from_article.local_course.curriculum.inventory import TopicSeed

_EXCERPT_LIMIT = 9_000
_TEACHING_UNIT_MIN_CHARS = 1_500
_WORD = re.compile(r"[A-Za-zА-Яа-яЁё0-9_]{4,}")
_COMMON_WORDS = {
    "будет",
    "были",
    "есть",
    "если",
    "когда",
    "который",
    "можно",
    "после",
    "также",
    "того",
    "чтобы",
    "about",
    "after",
    "also",
    "from",
    "that",
    "then",
    "there",
    "these",
    "this",
    "when",
    "with",
}
_SHELL_CLOSING_RE = re.compile(
    r"^(?:"
    r"заключение|подведение итогов|итоги?|вместо заключения|послесловие|"
    r"что (?:изучать |читать )?дальше|полезные ссылки|источники|литература|"
    r"дополнительн\w*\s+ресурс\w*|полезн\w*\s+ресурс\w*|"
    r"практическ\w*\s+примеры?|база\s+теории|базовая\s+теория|"
    r"conclusion|summary|wrap-?up|what'?s next|further reading|references|"
    r"additional\s+resources?|useful\s+resources?|more\s+resources?|"
    r"getting\s+started|next\s+steps|practical\s+examples?"
    r")\b",
    re.IGNORECASE,
)
_TRANSITION_TITLE_RE = re.compile(
    r"^(?:"
    r"переход\s+к\s+следующ\w*"
    r"|далее\s*[-—:.]"
    r"|next\s+section"
    r"|transition\s+to\s+(?:the\s+)?next"
    r")",
    re.IGNORECASE,
)
_SOURCE_CHROME_TITLE_RE = re.compile(
    r"^(?:table\s+of\s+contents|ask\s+\S+(?:\s+\S+)?|"
    r"(?:students?|contributors?|authors?)\s+on\s+\S.+|"
    r"(?:fast|easy|simple|powerful),\s+\w+\s+\w+\s+of\s+your\s+\S.+|"
    r"\w+,\s*\w+(?:\s+and\s+\w+)?\s+any\s+\S.+,\s*\w+)$",
    re.IGNORECASE,
)
_CODE_FRAGMENT_TITLE_RE = re.compile(
    r"^(?:"
    r"(?:get|set|return|yield|raise|import|from|await|print|call|run|use|make|take|see|try)\b"
    r"[\w\s'`,.():\-]{0,48}[.]?"
    r"|(?:async\s+)?def\s+\w+"
    r"|class\s+\w+"
    r")$",
    re.IGNORECASE,
)
_CONTRAST_EXAMPLE_RE = re.compile(
    r"^(?:"
    r"(?:плохой|хороший|bad|good|wrong|right|anti[- ]?pattern)\s+"
    r"(?:пример|example|case|образец)\b|"
    r"(?:пример|example)\s+(?:плохо|хорош|bad|good)\w*\b"
    r")",
    re.IGNORECASE,
)
_EXCERPT_SHELL_HEADING_RE = re.compile(
    r"^#{1,3}\s+(?:"
    r"заключение|итоги?|что\s+(?:изучать|читать)\s+дальше|"
    r"дополнительн\w*\s+ресурс\w*|полезн\w*\s+ресурс\w*|"
    r"conclusion|summary|wrap-?up|references|"
    r"further\s+reading|additional\s+resources?|what'?s\s+next"
    r")\b",
    re.IGNORECASE | re.MULTILINE,
)
_SHELL_WORD = re.compile(r"[\wё'-]+", re.IGNORECASE)

_SHELL_WORDS = frozenset(
    {
        "введение",
        "вводная",
        "вводный",
        "вступление",
        "предыстория",
        "обзор",
        "общая",
        "общие",
        "объяснение",
        "пояснение",
        "информация",
        "сведения",
        "тема",
        "темы",
        "раздел",
        "часть",
        "глава",
        "пример",
        "примеры",
        "листинг",
        "код",
        "содержание",
        "оглавление",
        "начало",
        "и",
        "в",
        "о",
        "об",
        "про",
        "к",
        "для",
        "background",
        "chapter",
        "code",
        "contents",
        "example",
        "examples",
        "explanation",
        "general",
        "intro",
        "introduction",
        "listing",
        "overview",
        "part",
        "preface",
        "section",
        "toc",
        "topic",
        "a",
        "an",
        "of",
        "the",
    }
)


def _drop_window_overlap(left: str, right: str) -> str:

    tail = split_sentences(left)
    head = split_sentences(right)
    if not tail or not head or tail[-1] != head[0]:
        return right
    rest = " ".join(head[1:]).strip()
    return rest or right


def merge_excerpts(left: str, right: str, *, limit: int = _EXCERPT_LIMIT) -> str:
    left_text = left.strip()
    right_text = right.strip()
    if not right_text:
        return left_text[:limit]
    if not left_text:
        return right_text[:limit]
    if right_text in left_text:
        return left_text[:limit]
    if left_text in right_text:
        return right_text[:limit]
    right_text = _drop_window_overlap(left_text, right_text)
    return f"{left_text}\n\n{right_text}"[:limit]


def _sentence_terms(sentence: str) -> frozenset[str]:
    return frozenset(
        word.casefold() for word in _WORD.findall(sentence) if word.casefold() not in _COMMON_WORDS
    )


def _same_claim(left: frozenset[str], right: frozenset[str]) -> bool:
    if len(left) < 6 or len(right) < 6:
        return False
    return len(left & right) / min(len(left), len(right)) >= 0.82


def dedupe_seed_claims(seeds: list[TopicSeed]) -> list[TopicSeed]:

    seen: list[frozenset[str]] = []
    out: list[TopicSeed] = []
    for seed in seeds:
        excerpt = seed.excerpt
        for sentence in split_sentences(seed.excerpt):
            if len(sentence) < 80 or "\n" in sentence or sentence.lstrip().startswith("```"):
                continue
            terms = _sentence_terms(sentence)
            if any(_same_claim(terms, prior) for prior in seen):
                excerpt = excerpt.replace(sentence, "", 1)
                continue
            if len(terms) >= 6:
                seen.append(terms)
        excerpt = re.sub(r"[ \t]{2,}", " ", excerpt)
        excerpt = re.sub(r"\n{3,}", "\n\n", excerpt).strip()
        if excerpt:
            out.append(replace(seed, excerpt=excerpt))
    return out


def merge_thin_headingless_seeds(
    seeds: list[TopicSeed],
    *,
    min_chars: int = _TEACHING_UNIT_MIN_CHARS,
) -> list[TopicSeed]:

    out: list[TopicSeed] = []
    for seed in seeds:
        if (
            out
            and not seed.from_heading
            and not out[-1].from_heading
            and seed.source_title == out[-1].source_title
            and len(out[-1].excerpt) < min_chars
        ):
            prior = out[-1]
            out[-1] = replace(
                prior,
                excerpt=merge_excerpts(prior.excerpt, seed.excerpt),
                objective=prior.objective or seed.objective,
            )
            continue
        out.append(seed)
    if (
        len(out) >= 2
        and not out[-1].from_heading
        and not out[-2].from_heading
        and out[-1].source_title == out[-2].source_title
        and len(out[-1].excerpt) < min_chars
    ):
        tail = out.pop()
        prior = out[-1]
        out[-1] = replace(
            prior,
            excerpt=merge_excerpts(prior.excerpt, tail.excerpt),
            objective=prior.objective or tail.objective,
        )
    return out


def is_shell_title(title: str) -> bool:

    text = " ".join((title or "").split()).strip(" .:;—-")
    if not text:
        return True
    if _CODE_FRAGMENT_TITLE_RE.match(text):
        return True
    if _TRANSITION_TITLE_RE.match(text):
        return True
    if _SHELL_CLOSING_RE.match(text):
        return True
    if _SOURCE_CHROME_TITLE_RE.search(text):
        return True
    if _CONTRAST_EXAMPLE_RE.match(text):
        return True
    words = _SHELL_WORD.findall(text.casefold())
    return bool(words) and all(word in _SHELL_WORDS for word in words)


def is_shell_seed(seed: TopicSeed) -> bool:

    if is_shell_title(seed.title):
        return True
    excerpt = (seed.excerpt or "").lstrip()
    if not excerpt:
        return False
    first_block = excerpt.split("\n\n", 1)[0]
    return bool(_EXCERPT_SHELL_HEADING_RE.search(first_block))


def merge_shell_seeds(seeds: list[TopicSeed]) -> list[TopicSeed]:

    if len(seeds) < 2:
        return list(seeds)
    pool = list(seeds)
    index = 0
    while index < len(pool):
        seed = pool[index]
        if not is_shell_seed(seed):
            index += 1
            continue
        if index + 1 < len(pool):
            neighbor = pool[index + 1]
            pool[index + 1] = replace(
                neighbor,
                excerpt=merge_excerpts(seed.excerpt, neighbor.excerpt),
                objective=neighbor.objective or seed.objective,
            )
            del pool[index]
            continue
        if index > 0:
            neighbor = pool[index - 1]
            pool[index - 1] = replace(
                neighbor,
                excerpt=merge_excerpts(neighbor.excerpt, seed.excerpt),
                objective=neighbor.objective or seed.objective,
            )
            del pool[index]
            continue
        index += 1
    return pool


def _same_topic(left: TopicSeed, right: TopicSeed) -> bool:
    return topics_are_duplicates(
        left_title=left.title,
        left_excerpt=left.excerpt,
        right_title=right.title,
        right_excerpt=right.excerpt,
    )


def collapse_near_duplicates(seeds: list[TopicSeed]) -> list[TopicSeed]:
    kept: list[TopicSeed] = []
    for seed in seeds:
        twin_index = next(
            (index for index, prior in enumerate(kept) if _same_topic(seed, prior)),
            None,
        )
        if twin_index is None:
            kept.append(seed)
            continue
        prior = kept[twin_index]
        longer_objective = (
            prior.objective if len(prior.objective) >= len(seed.objective) else seed.objective
        )
        kept[twin_index] = replace(
            prior,
            excerpt=merge_excerpts(prior.excerpt, seed.excerpt),
            objective=longer_objective,
        )
    return kept


def _title_winner(left: TopicSeed, right: TopicSeed) -> TopicSeed:

    if left.from_heading != right.from_heading:
        return left if left.from_heading else right
    return left if len(left.title) >= len(right.title) else right


def merge_semantic_groups(
    seeds: list[TopicSeed],
    ordered: list[TopicSeed],
    groups: list[list[str]],
    *,
    min_topics: int = 1,
) -> list[TopicSeed]:

    representative: dict[int, TopicSeed] = {}
    remaining = len(ordered)
    for raw_group in groups:
        indexes = sorted(
            {int(item) for item in raw_group if item.isdigit() and 0 <= int(item) < len(seeds)}
        )
        if len(indexes) < 2 or any(index in representative for index in indexes):
            continue
        # Модель иногда просит слить почти весь список: держим план не ниже объёма корпуса.
        if remaining - (len(indexes) - 1) < max(1, min_topics):
            continue
        remaining -= len(indexes) - 1
        members = [seeds[index] for index in indexes]
        winner = members[0]
        excerpt = winner.excerpt
        objective = winner.objective
        for member in members[1:]:
            winner = _title_winner(winner, member)
            excerpt = merge_excerpts(excerpt, member.excerpt)
            if len(member.objective) > len(objective):
                objective = member.objective
        merged = TopicSeed(
            title=winner.title,
            objective=objective,
            excerpt=excerpt,
            source_title=winner.source_title,
            order=min(member.order for member in members),
            from_heading=winner.from_heading,
        )
        for index in indexes:
            representative[index] = merged

    index_by_identity = {id(seed): index for index, seed in enumerate(seeds)}
    out: list[TopicSeed] = []
    emitted: set[int] = set()
    for seed in ordered:
        index = index_by_identity.get(id(seed))
        item = representative.get(index, seed) if index is not None else seed
        marker = id(item)
        if marker in emitted:
            continue
        emitted.add(marker)
        out.append(item)
    return out


def merge_adjacent_to_cap(seeds: list[TopicSeed], *, cap: int) -> list[TopicSeed]:
    if cap < 1:
        return seeds[:1]
    pool = list(seeds)
    while len(pool) > cap and len(pool) >= 2:
        best = 0
        best_size = len(pool[0].excerpt) + len(pool[1].excerpt)
        for index in range(1, len(pool) - 1):
            size = len(pool[index].excerpt) + len(pool[index + 1].excerpt)
            if size < best_size:
                best = index
                best_size = size
        left = pool[best]
        right = pool[best + 1]
        winner = _title_winner(left, right)
        pool[best : best + 2] = [
            TopicSeed(
                title=winner.title,
                objective=left.objective or right.objective,
                excerpt=merge_excerpts(left.excerpt, right.excerpt),
                source_title=left.source_title,
                order=left.order,
                from_heading=winner.from_heading,
            )
        ]
    return pool


def _split_seed(seed: TopicSeed) -> tuple[TopicSeed, TopicSeed] | None:
    blocks = [block.strip() for block in seed.excerpt.split("\n\n") if len(block.strip()) >= 200]
    if len(blocks) < 2:
        blocks = [
            unit.strip()
            for unit in split_source_units(seed.excerpt, sentences_per_window=4)
            if len(unit.strip()) >= 200
        ]
    if len(blocks) < 2:
        return None
    pivot = max(1, len(blocks) // 2)
    left_excerpt = "\n\n".join(blocks[:pivot]).strip()
    right_excerpt = "\n\n".join(blocks[pivot:]).strip()
    if len(left_excerpt) < 200 or len(right_excerpt) < 200:
        return None
    right_heading = ""
    if match := re.match(r"^#{1,3}\s+(\S.*?)\s*$", blocks[pivot]):
        right_heading = match.group(1).strip()
    right_title = (
        right_heading
        if right_heading and not is_shell_title(right_heading)
        else (f"{seed.title[:48]} (2)")
    )
    return (
        replace(seed, excerpt=left_excerpt),
        replace(
            seed,
            title=right_title,
            excerpt=right_excerpt,
            order=seed.order + 1,
            from_heading=bool(right_heading),
        ),
    )


def expand_seeds_to_floor(
    seeds: list[TopicSeed],
    *,
    min_topics: int,
    max_chapters: int,
) -> list[TopicSeed]:
    if min_topics <= 1 or len(seeds) >= min_topics:
        return list(seeds)[:max_chapters]
    pool = list(seeds)
    while len(pool) < min_topics and len(pool) < max_chapters:
        pool.sort(key=lambda item: len(item.excerpt), reverse=True)
        split = _split_seed(pool[0])
        if split is None:
            break
        left, right = split
        pool[0] = left
        pool.insert(1, right)
    return pool[:max_chapters]


def ensure_inventory_floor(
    raw_seeds: list[TopicSeed],
    fitted: list[TopicSeed],
    *,
    min_topics: int,
    max_chapters: int,
) -> list[TopicSeed]:
    if len(fitted) >= min_topics:
        return fitted[:max_chapters]
    by_source: dict[str, TopicSeed] = {}
    for seed in raw_seeds:
        key = seed.source_title or seed.title
        current = by_source.get(key)
        if current is None or len(seed.excerpt) > len(current.excerpt):
            by_source[key] = seed
    per_source = [seed for seed in by_source.values() if not is_shell_seed(seed)]
    if len(per_source) >= min_topics:
        return per_source[:max_chapters]
    return expand_seeds_to_floor(
        fitted or per_source,
        min_topics=min_topics,
        max_chapters=max_chapters,
    )


def fit_seed_count(
    seeds: list[TopicSeed],
    *,
    max_chapters: int,
    min_topics: int = 1,
) -> list[TopicSeed]:
    return prepare_corpus(seeds, max_chapters=max_chapters, min_topics=min_topics)


def prepare_corpus(
    seeds: list[TopicSeed],
    *,
    max_chapters: int,
    min_topics: int = 1,
) -> list[TopicSeed]:

    unique_claims = dedupe_seed_claims(seeds)
    topical = merge_shell_seeds(collapse_near_duplicates(unique_claims))
    merged = merge_thin_headingless_seeds(topical)
    teachable = [seed for seed in merged if not is_shell_seed(seed)]

    pool = teachable or merged or list(seeds)
    if len(pool) > max_chapters:
        pool = merge_adjacent_to_cap(pool, cap=max_chapters)
    return ensure_inventory_floor(seeds, pool, min_topics=min_topics, max_chapters=max_chapters)
