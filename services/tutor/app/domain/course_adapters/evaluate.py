from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.domain.course_from_article.curriculum.theory.theory_sections import split_source_units
from app.domain.course_from_article.local_course.content.fallbacks import (
    practice_from_chapter_theory,
    quizzes_from_chapter_theory,
    template_practice_from_objective,
    template_quizzes_from_objective,
)
from app.domain.course_from_article.local_course.curriculum.collapse import fit_seed_count
from app.domain.course_from_article.local_course.curriculum.compiler import (
    order_seeds_heuristic,
    seeds_to_chapters,
)
from app.domain.course_from_article.local_course.curriculum.inventory import inventory_from_sources
from app.domain.course_from_article.local_course.policy.heuristics import (
    practice_spec_is_usable,
    quiz_item_is_usable,
)

from .eval_corpus import EVAL_ARTICLES, EvalArticle
from .roles import AdapterRefused, AdapterRole

ProduceDraft = Callable[[EvalArticle], "CourseDraft"]

_HEADING_WEIGHT = 0.4
_QUIZ_WEIGHT = 0.35
_PRACTICE_WEIGHT = 0.25
_COVERAGE_SLACK = 0.02


@dataclass(frozen=True, slots=True)
class CourseDraft:
    chapters: list[dict[str, str]]
    quizzes: list[dict[str, object]]
    practice: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class ArticleScore:
    title: str
    heading_coverage: float
    quiz_grounded: float
    practice_io: float

    @property
    def overall(self) -> float:
        return (
            _HEADING_WEIGHT * self.heading_coverage
            + _QUIZ_WEIGHT * self.quiz_grounded
            + _PRACTICE_WEIGHT * self.practice_io
        )

    def to_dict(self) -> dict[str, float | str]:
        return {
            "title": self.title,
            "heading_coverage": self.heading_coverage,
            "quiz_grounded": self.quiz_grounded,
            "practice_io": self.practice_io,
        }


@dataclass(frozen=True, slots=True)
class EvalReport:
    scores: tuple[ArticleScore, ...]

    @property
    def article_count(self) -> int:
        return len(self.scores)

    @property
    def mean(self) -> float:
        if not self.scores:
            return 0.0
        return sum(item.overall for item in self.scores) / len(self.scores)

    @property
    def coverage_mean(self) -> float:
        if not self.scores:
            return 0.0
        return sum(item.heading_coverage for item in self.scores) / len(self.scores)

    def to_dict(self) -> dict[str, object]:
        return {
            "article_count": self.article_count,
            "mean": self.mean,
            "coverage_mean": self.coverage_mean,
            "scores": [item.to_dict() for item in self.scores],
        }


def _finite_float(raw: object) -> float | None:
    if isinstance(raw, bool) or not isinstance(raw, int | float | str):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value != value:
        return None
    return value


def report_from_dict(raw: object) -> EvalReport:
    if not isinstance(raw, dict):
        raise AdapterRefused("eval report must be an object")
    rows = raw.get("scores")
    if not isinstance(rows, list) or not rows:
        raise AdapterRefused("eval report has no scores")
    scores: list[ArticleScore] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        coverage = _finite_float(item.get("heading_coverage"))
        quiz = _finite_float(item.get("quiz_grounded"))
        practice = _finite_float(item.get("practice_io"))
        if coverage is None or quiz is None or practice is None:
            continue
        scores.append(
            ArticleScore(
                title=str(item.get("title") or ""),
                heading_coverage=coverage,
                quiz_grounded=quiz,
                practice_io=practice,
            )
        )
    if not scores:
        raise AdapterRefused("eval report scores are empty")
    return EvalReport(scores=tuple(scores))


def _headings(body: str) -> list[str]:
    return [
        unit.split("\n", 1)[0].lstrip("#").strip()
        for unit in split_source_units(body, sentences_per_window=8)
        if unit.strip()
    ]


def score_draft(article: EvalArticle, draft: CourseDraft) -> ArticleScore:
    headings = _headings(article.body)
    blob = " ".join(
        f"{item.get('title', '')} {item.get('source_excerpt', '')}" for item in draft.chapters
    ).casefold()
    hits = sum(heading.casefold() in blob for heading in headings)
    coverage = hits / len(headings) if headings else 0.0
    theory = " ".join(str(item.get("source_excerpt") or "") for item in draft.chapters)
    quiz_rate = (
        sum(quiz_item_is_usable(quiz, theory=theory, locale=None) for quiz in draft.quizzes)
        / len(draft.quizzes)
        if draft.quizzes
        else 0.0
    )
    practice_rate = (
        sum(practice_spec_is_usable(task, locale=None) for task in draft.practice)
        / len(draft.practice)
        if draft.practice
        else 0.0
    )
    return ArticleScore(
        title=article.title,
        heading_coverage=coverage,
        quiz_grounded=quiz_rate,
        practice_io=practice_rate,
    )


def compiler_draft(article: EvalArticle) -> CourseDraft:
    seeds = inventory_from_sources(
        [{"title": article.title, "content": article.body}],
        sentences_per_window=3,
    )
    fitted = fit_seed_count(seeds, max_chapters=100)
    chapters = seeds_to_chapters(order_seeds_heuristic(fitted), max_chapters=100)
    quizzes: list[dict[str, object]] = []
    practice: list[dict[str, object]] = []
    for chapter in chapters:
        excerpt = chapter.get("source_excerpt") or ""
        grounded = quizzes_from_chapter_theory(
            chapter=chapter,
            theory=excerpt,
            count=1,
            topic_key=chapter["id"],
            locale="en",
        )
        if grounded:
            quizzes.extend(grounded)
        else:
            quizzes.extend(
                template_quizzes_from_objective(
                    chapter=chapter,
                    count=1,
                    topic_key=chapter["id"],
                    theory=excerpt,
                )
            )
        drills = practice_from_chapter_theory(
            chapter=chapter,
            theory=excerpt,
            count=1,
            topic_key=chapter["id"],
            locale="en",
        )
        if drills:
            practice.extend(drills)
        else:
            practice.extend(
                template_practice_from_objective(
                    chapter=chapter,
                    count=1,
                    topic_key=chapter["id"],
                )
            )
    return CourseDraft(chapters=chapters, quizzes=quizzes, practice=practice)


def evaluate_corpus(
    produce: ProduceDraft,
    *,
    articles: tuple[EvalArticle, ...] | None = None,
) -> EvalReport:
    corpus = articles if articles is not None else EVAL_ARTICLES
    scores = tuple(score_draft(article, produce(article)) for article in corpus)
    return EvalReport(scores=scores)


def compiler_baseline(
    articles: tuple[EvalArticle, ...] | None = None,
) -> EvalReport:
    return evaluate_corpus(compiler_draft, articles=articles)


def adapter_beats_compiler(adapter: EvalReport, compiler: EvalReport) -> bool:
    if adapter.article_count < 20 or compiler.article_count < 20:
        return False
    if adapter.article_count != compiler.article_count:
        return False
    if adapter.coverage_mean + 1e-9 < compiler.coverage_mean - _COVERAGE_SLACK:
        return False
    return adapter.mean > compiler.mean


def assert_adapter_ships(
    *,
    role: AdapterRole,
    adapter: EvalReport,
    compiler: EvalReport,
) -> None:
    if not adapter_beats_compiler(adapter, compiler):
        raise AdapterRefused(
            f"{role} adapter mean={adapter.mean:.3f} "
            f"does not beat compiler mean={compiler.mean:.3f} "
            f"on {compiler.article_count} articles"
        )
