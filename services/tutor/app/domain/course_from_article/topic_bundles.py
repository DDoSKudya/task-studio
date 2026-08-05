from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
from app.domain.course_build import CourseBuildStore
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .practice_generate import generate_code_tasks, generate_open_tasks
from .progress import _band_progress, _stage_event
from .quiz_generate import generate_quizzes
from .source_exercise_harvest import HarvestedExercise
from .textutil import _slug
from .theory_expand import _expand_one_theory_chapter
from .theory_split import split_long_theory_steps


@dataclass
class TopicBundleResult:
    theory_steps: list[dict[str, object]] = field(default_factory=list)
    quiz_steps: list[dict[str, object]] = field(default_factory=list)
    code_steps: list[dict[str, object]] = field(default_factory=list)


def _per_topic_counts(
    body: CourseFromArticleRequest,
    *,
    topic_total: int,
    compact: bool = False,
) -> tuple[int, int]:
    _ = compact
    quiz_total = max(1, body.effective_quiz_count())
    practice_total = max(0, body.effective_practice_count())
    quizzes = max(1, quiz_total // max(1, topic_total))
    practice = max(0, practice_total // max(1, topic_total))
    return quizzes, practice


def _namespace_step_id(step: dict[str, object], topic_key: str) -> None:
    """Keep per-topic quiz/code ids unique so assemble does not collapse them."""
    raw = step.get("id")
    if not isinstance(raw, str) or not raw.strip():
        return
    step_id = raw.strip()
    prefix = f"{topic_key}--"
    if step_id.startswith(prefix):
        return
    step["id"] = f"{prefix}{step_id}"[:96]


async def iter_topic_bundle_stages(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    domain: str,
    use_code: bool,
    use_open: bool,
    band: tuple[float, float],
    warnings: list[str],
    result: TopicBundleResult,
    store: CourseBuildStore | None = None,
    user_id: uuid.UUID | None = None,
    build_id: uuid.UUID | None = None,
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> AsyncIterator[dict[str, object]]:
    topic_total = len(chapters)
    if topic_total == 0:
        return

    done_ids: set[str] = set()
    if store is not None and user_id is not None and build_id is not None:
        done_ids = store.list_topic_ids(user_id, build_id)
        if done_ids:
            saved_theory, saved_quizzes, saved_codes = store.load_topics(user_id, build_id)
            result.theory_steps.extend(saved_theory)
            result.quiz_steps.extend(saved_quizzes)
            result.code_steps.extend(saved_codes)

    for index, chapter in enumerate(chapters):
        chapter_id = chapter["id"]
        topic_key = _slug(chapter_id)[:40] or chapter_id
        if chapter_id in done_ids:
            yield _stage_event(
                stage="topic_bundle",
                status="done",
                progress=_band_progress(band, index + 1, topic_total),
                message=f"Topic bundle restored: {chapter['title']}",
                message_key="topicBundleRestored",
                message_params={"title": chapter["title"]},
                index=index + 1,
                total=topic_total,
                detail={"chapter_id": chapter_id, "restored": True},
            )
            continue

        yield _stage_event(
            stage="topic_bundle",
            status="running",
            progress=_band_progress(band, index, topic_total),
            message=f"Building topic bundle: {chapter['title']}",
            message_key="topicBundleRunning",
            message_params={"title": chapter["title"]},
            index=index + 1,
            total=topic_total,
            detail={"chapter_id": chapter_id, "chapter_title": chapter["title"]},
        )

        theory_steps: list[dict[str, object]] = []
        topic_quizzes: list[dict[str, object]] = []
        topic_codes: list[dict[str, object]] = []

        if body.include_theory:
            theory_step = await _expand_one_theory_chapter(
                client,
                target,
                body=body,
                compact=compact,
                chapter=chapter,
                chapters=chapters,
                outcomes=outcomes,
                book_spine=book_spine,
                index=index,
            )
            if theory_step:
                theory_step["chapter_id"] = topic_key
                theory_steps = split_long_theory_steps(
                    [theory_step],
                    enabled=body.split_long_theory,
                )
                result.theory_steps.extend(theory_steps)

        per_quiz, per_practice = _per_topic_counts(
            body,
            topic_total=topic_total,
            compact=compact,
        )

        if body.include_quizzes:
            topic_body = body.model_copy(update={"quiz_count": per_quiz})
            topic_quizzes = await generate_quizzes(
                client,
                target,
                body=topic_body,
                compact=compact,
                chapters=[chapter],
                outcomes=outcomes,
                theory_steps=theory_steps,
                exercise_seeds=exercise_seeds,
            )
            for quiz in topic_quizzes:
                quiz["chapter_id"] = topic_key
                _namespace_step_id(quiz, topic_key)
            result.quiz_steps.extend(topic_quizzes)

        if use_code:
            topic_body = body.model_copy(update={"code_count": max(1, per_practice)})
            topic_codes = await generate_code_tasks(
                client,
                target,
                body=topic_body,
                compact=compact,
                chapters=[chapter],
                outcomes=outcomes,
                exercise_seeds=exercise_seeds,
            )
            for code in topic_codes:
                code["chapter_id"] = topic_key
                _namespace_step_id(code, topic_key)
            result.code_steps.extend(topic_codes)
        elif use_open and body.include_code:
            topic_body = body.model_copy(update={"code_count": max(1, per_practice)})
            topic_codes = await generate_open_tasks(
                client,
                target,
                body=topic_body,
                compact=compact,
                chapters=[chapter],
                outcomes=outcomes,
                domain=domain,
            )
            for code in topic_codes:
                code["chapter_id"] = topic_key
                _namespace_step_id(code, topic_key)
            result.code_steps.extend(topic_codes)

        if store is not None and user_id is not None and build_id is not None:
            store.save_topic(
                user_id,
                build_id,
                chapter_id,
                theories=theory_steps,
                quizzes=topic_quizzes,
                codes=topic_codes,
            )
            done_ids.add(chapter_id)
            store.patch_meta(
                user_id,
                build_id,
                stage="topic_bundle",
                chapters_done=len(done_ids),
                chapter_total=topic_total,
                progress=_band_progress(band, index + 1, topic_total),
                message=f"Topic bundle ready: {chapter['title']}",
                clear_error=True,
            )

        yield _stage_event(
            stage="topic_bundle",
            status="done",
            progress=_band_progress(band, index + 1, topic_total),
            message=f"Topic bundle ready: {chapter['title']}",
            message_key="topicBundleDone",
            message_params={"title": chapter["title"]},
            index=index + 1,
            total=topic_total,
            detail={
                "chapter_id": chapter_id,
                "theory": len(theory_steps),
                "quizzes": per_quiz if body.include_quizzes else 0,
                "practice": per_practice if body.include_code else 0,
            },
        )
