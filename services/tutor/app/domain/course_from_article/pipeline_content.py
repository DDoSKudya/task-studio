from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
from app.domain.course_build import CourseBuildStore
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .polish import _iter_book_polish
from .progress import _stage_event
from .source_exercise_harvest import HarvestedExercise
from .stages import (
    _iter_practice_stage,
    _iter_quizzes_and_code_parallel,
    _iter_quizzes_stage,
)
from .theory import _iter_theory_expansion


@dataclass
class ContentStageResult:
    theory_steps: list[dict[str, object]] = field(default_factory=list)
    quiz_steps: list[dict[str, object]] = field(default_factory=list)
    code_steps: list[dict[str, object]] = field(default_factory=list)


async def iter_content_stages(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    domain: str,
    band_theory: tuple[float, float],
    band_polish: tuple[float, float],
    band_quizzes: tuple[float, float],
    band_code: tuple[float, float],
    warnings: list[str],
    result: ContentStageResult,
    use_code: bool = True,
    use_open: bool = False,
    practice_is_open: bool = False,
    store: CourseBuildStore | None = None,
    user_id: uuid.UUID | None = None,
    build_id: uuid.UUID | None = None,
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> AsyncIterator[dict[str, object]]:
    theory_steps = result.theory_steps
    quiz_steps = result.quiz_steps
    code_steps = result.code_steps

    if body.include_theory:
        async for event in _iter_theory_expansion(
            client,
            target,
            body=body,
            compact=compact,
            chapters=chapters,
            outcomes=outcomes,
            book_spine=book_spine,
            band_theory=band_theory,
            theory_steps=theory_steps,
            store=store,
            user_id=user_id,
            build_id=build_id,
        ):
            yield event

        if len(theory_steps) >= 2 and not compact:
            async for event in _iter_book_polish(
                client,
                target,
                body=body,
                compact=compact,
                chapters=chapters,
                book_spine=book_spine,
                band_polish=band_polish,
                theory_steps=theory_steps,
                warnings=warnings,
            ):
                yield event
        elif compact and theory_steps:
            warnings.append("book polish skipped for local model (speed)")
            yield _stage_event(
                stage="polish",
                status="done",
                progress=band_polish[1],
                message="Book polish skipped for local model",
                message_key="polishSkippedLocal",
                detail={"skipped": True, "reason": "compact", "chapter_count": len(theory_steps)},
            )
        elif theory_steps:
            yield _stage_event(
                stage="polish",
                status="done",
                progress=band_polish[1],
                message="Book polish applied to 0 chapter(s)",
                message_key="polishDone",
                message_params={"count": 0},
                detail={"edits_applied": 0, "chapter_count": len(theory_steps), "skipped": True},
            )

    restored_quizzes = (
        store.load_quizzes(user_id, build_id)
        if store is not None and user_id is not None and build_id is not None
        else None
    )
    restored_codes = (
        store.load_codes(user_id, build_id)
        if store is not None and user_id is not None and build_id is not None
        else None
    )

    if body.include_quizzes and restored_quizzes is not None:
        quiz_steps.extend(restored_quizzes)
        yield _stage_event(
            stage="quizzes",
            status="done",
            progress=band_quizzes[1],
            message=f"Quizzes restored ({len(restored_quizzes)})",
            message_key="quizzesRestored",
            message_params={"count": len(restored_quizzes)},
            detail={"restored": True, "count": len(restored_quizzes)},
        )
    if body.include_code and restored_codes is not None:
        code_steps.extend(restored_codes)
        yield _stage_event(
            stage="code",
            status="done",
            progress=band_code[1],
            message=f"Practice restored ({len(restored_codes)})",
            message_key="codeRestored",
            message_params={"count": len(restored_codes)},
            detail={"restored": True, "count": len(restored_codes)},
        )

    need_quizzes = body.include_quizzes and restored_quizzes is None
    need_code = body.include_code and restored_codes is None

    if need_quizzes and need_code and not compact:
        async for event in _iter_quizzes_and_code_parallel(
            client,
            target,
            body=body,
            compact=compact,
            chapters=chapters,
            outcomes=outcomes,
            theory_steps=theory_steps,
            band_quizzes=band_quizzes,
            band_code=band_code,
            quiz_steps_out=quiz_steps,
            code_steps_out=code_steps,
            domain=domain,
            practice_is_open=practice_is_open or (use_open and not use_code),
            exercise_seeds=exercise_seeds,
        ):
            yield event
        if store is not None and user_id is not None and build_id is not None:
            store.save_quizzes(user_id, build_id, quiz_steps)
            store.save_codes(user_id, build_id, code_steps)
        return

    if need_quizzes:
        async for event in _iter_quizzes_stage(
            client,
            target,
            body=body,
            compact=compact,
            chapters=chapters,
            outcomes=outcomes,
            theory_steps=theory_steps,
            band_quizzes=band_quizzes,
            quiz_steps_out=quiz_steps,
            exercise_seeds=exercise_seeds,
        ):
            yield event
        if store is not None and user_id is not None and build_id is not None:
            store.save_quizzes(user_id, build_id, quiz_steps)

    if need_code:
        async for event in _iter_practice_stage(
            client,
            target,
            body=body,
            compact=compact,
            chapters=chapters,
            outcomes=outcomes,
            band_code=band_code,
            code_steps_out=code_steps,
            domain=domain,
            prefer_open=practice_is_open or (use_open and not use_code),
            exercise_seeds=exercise_seeds,
        ):
            yield event
        if store is not None and user_id is not None and build_id is not None:
            store.save_codes(user_id, build_id, code_steps)
