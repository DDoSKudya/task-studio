from __future__ import annotations

_MAX_ARTICLE_FOR_PROMPT = 48_000
_MAX_ARTICLE_FOR_PROMPT_COMPACT = 28_000
_MAX_CHAPTERS = 100
_MAX_CHAPTERS_COMPACT = 8
_MAX_SOURCE_EXCERPT = 9_000
_MAX_SOURCE_EXCERPT_COMPACT = 2_800

_THEORY_SERIAL_PREFIX = 2
_THEORY_PARALLEL_LIMIT = 3
_COURSE_STREAM_PING_SECONDS = 12.0

_BAND_ANALYZE = (0.0, 0.14)
_BAND_THEORY = (0.14, 0.48)
_BAND_POLISH = (0.48, 0.56)
_BAND_QUIZZES = (0.56, 0.74)
_BAND_CODE = (0.74, 0.90)
_BAND_ASSEMBLE = (0.90, 1.0)

_BAND_ANALYZE_SOLO = (0.0, 0.12)
_BAND_THEORY_SOLO = (0.12, 0.50)
_BAND_POLISH_SOLO = (0.50, 0.55)
_BAND_QUIZZES_SOLO = (0.55, 0.72)
_BAND_CODE_SOLO = (0.72, 0.90)
_BAND_ASSEMBLE_SOLO = (0.90, 1.0)

_STAGE_WEIGHTS: dict[str, float] = {
    "analyze": 0.14,
    "theory": 0.34,
    "polish": 0.08,
    "quizzes": 0.16,
    "code": 0.16,
    "assemble": 0.12,
}


def _allocate_progress_bands(
    *,
    include_theory: bool,
    include_quizzes: bool,
    include_code: bool,
) -> dict[str, tuple[float, float]]:
    order: list[str] = ["analyze"]
    if include_theory:
        order.extend(("theory", "polish"))
    if include_quizzes:
        order.append("quizzes")
    if include_code:
        order.append("code")
    order.append("assemble")

    total = sum(_STAGE_WEIGHTS[name] for name in order) or 1.0
    cursor = 0.0
    bands: dict[str, tuple[float, float]] = {}
    for index, name in enumerate(order):
        span = _STAGE_WEIGHTS[name] / total
        start = round(cursor, 4)
        cursor += span
        end = 1.0 if index == len(order) - 1 else round(cursor, 4)
        bands[name] = (start, end)
    return bands
