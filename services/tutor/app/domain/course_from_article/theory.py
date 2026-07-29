from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .progress import _band_progress, _stage_event
from .theory_expand import (
    _await_indexed,
    _expand_one_theory_chapter,
    _theory_parallel_limit,
    _theory_serial_count,
)

__all__ = [
    "_await_indexed",
    "_expand_one_theory_chapter",
    "_iter_theory_expansion",
    "_theory_parallel_limit",
    "_theory_serial_count",
]


async def _iter_theory_expansion(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    band_theory: tuple[float, float],
    theory_steps: list[dict[str, object]],
) -> AsyncIterator[dict[str, object]]:
    chapter_total = len(chapters)
    serial_n = _theory_serial_count(chapter_total, compact=compact)
    done = 0

    for index in range(serial_n):
        chapter = chapters[index]
        yield _stage_event(
            stage="theory",
            status="running",
            progress=_band_progress(band_theory, done, chapter_total),
            message=f"Expanding chapter: {chapter['title']}",
            message_key="theoryExpanding",
            message_params={"title": chapter["title"]},
            index=index + 1,
            total=chapter_total,
            detail={
                "chapter_id": chapter["id"],
                "chapter_title": chapter["title"],
                "mode": "serial",
            },
        )
        step = await _expand_one_theory_chapter(
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
        theory_steps.append(step)
        done += 1
        yield _stage_event(
            stage="theory",
            status="done",
            progress=_band_progress(band_theory, done, chapter_total),
            message=f"Theory ready: {step.get('title')}",
            message_key="theoryReady",
            message_params={"title": step.get("title") or ""},
            index=index + 1,
            total=chapter_total,
            detail={
                "step_id": step.get("id"),
                "title": step.get("title"),
                "content_chars": len(str(step.get("content") or "")),
                "mode": "serial",
            },
        )

    remaining = list(enumerate(chapters))[serial_n:]
    if not remaining:
        return

    limit = _theory_parallel_limit(compact=compact)
    if limit <= 1 or len(remaining) == 1:
        for index, chapter in remaining:
            yield _stage_event(
                stage="theory",
                status="running",
                progress=_band_progress(band_theory, done, chapter_total),
                message=f"Expanding chapter: {chapter['title']}",
                message_key="theoryExpanding",
                message_params={"title": chapter["title"]},
                index=index + 1,
                total=chapter_total,
                detail={
                    "chapter_id": chapter["id"],
                    "chapter_title": chapter["title"],
                    "mode": "serial",
                },
            )
            step = await _expand_one_theory_chapter(
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
            theory_steps.append(step)
            done += 1
            yield _stage_event(
                stage="theory",
                status="done",
                progress=_band_progress(band_theory, done, chapter_total),
                message=f"Theory ready: {step.get('title')}",
                message_key="theoryReady",
                message_params={"title": step.get("title") or ""},
                index=index + 1,
                total=chapter_total,
                detail={
                    "step_id": step.get("id"),
                    "title": step.get("title"),
                    "content_chars": len(str(step.get("content") or "")),
                    "mode": "serial",
                },
            )
        return

                                                                                      
    for index, chapter in remaining:
        yield _stage_event(
            stage="theory",
            status="running",
            progress=_band_progress(band_theory, done, chapter_total),
            message=f"Expanding chapter: {chapter['title']}",
            message_key="theoryExpanding",
            message_params={"title": chapter["title"]},
            index=index + 1,
            total=chapter_total,
            detail={
                "chapter_id": chapter["id"],
                "chapter_title": chapter["title"],
                "mode": "parallel",
                "parallel_limit": limit,
            },
        )

    semaphore = asyncio.Semaphore(limit)
    tasks = [
        asyncio.create_task(
            _expand_one_theory_chapter(
                client,
                target,
                body=body,
                compact=compact,
                chapter=chapter,
                chapters=chapters,
                outcomes=outcomes,
                book_spine=book_spine,
                index=index,
                semaphore=semaphore,
            )
        )
        for index, chapter in remaining
    ]
    ordered: list[dict[str, object] | None] = [None] * len(remaining)
    for finished in asyncio.as_completed(
        [
            asyncio.create_task(_await_indexed(task_index, task))
            for task_index, task in enumerate(tasks)
        ]
    ):
        slot, step = await finished
        index, chapter = remaining[slot]
        ordered[slot] = step
        done += 1
        yield _stage_event(
            stage="theory",
            status="done",
            progress=_band_progress(band_theory, done, chapter_total),
            message=f"Theory ready: {step.get('title')}",
            message_key="theoryReady",
            message_params={"title": step.get("title") or ""},
            index=index + 1,
            total=chapter_total,
            detail={
                "step_id": step.get("id"),
                "title": step.get("title"),
                "content_chars": len(str(step.get("content") or "")),
                "mode": "parallel",
            },
        )

    for step in ordered:
        if step is None:
            raise TutorError(status.HTTP_502_BAD_GATEWAY, "course theory stage missing chapter")
        theory_steps.append(step)
