from __future__ import annotations

from studio_contracts.api.studio_schemas import CourseFromArticleRequest

_CHARS_PER_CHAPTER = 9_000

_DEPTH_STRETCH = 2


def corpus_char_count(
    sources: list[dict[str, object]] | None,
    article: str = "",
) -> int:

    if sources:
        total = sum(len(str(item.get("content") or "")) for item in sources)
        if total:
            return total
    return len(article)


def chapter_ceiling(
    body: CourseFromArticleRequest,
    *,
    corpus_chars: int,
    hard_max: int,
) -> int:

    hard = max(1, hard_max)
    if body.theory_count is not None:
        return max(1, min(body.theory_count, hard))

    floor = min(body.effective_theory_count() or hard, hard)
    supported = max(0, corpus_chars) // _CHARS_PER_CHAPTER
    return max(floor, min(hard, floor * _DEPTH_STRETCH, supported))


def chapter_floor(
    body: CourseFromArticleRequest,
    *,
    corpus_chars: int,
    ceiling: int,
) -> int:
    """Сколько глав корпус обязан выдержать: ниже этого числа курс схлопнут, а не сжат."""

    cap = max(1, ceiling)
    supported = max(0, corpus_chars) // _CHARS_PER_CHAPTER
    wanted = body.effective_theory_count() or cap
    return max(1, min(cap, wanted, supported))
