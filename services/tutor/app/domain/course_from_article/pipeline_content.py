from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .polish import _iter_book_polish
from .progress import _stage_event
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
        ):
            yield event

        if len(theory_steps) >= 2:
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

    if body.include_quizzes and body.include_code and not compact:
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
        ):
            yield event
        return

    if body.include_quizzes:
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
        ):
            yield event

    if body.include_code:
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
        ):
            yield event
