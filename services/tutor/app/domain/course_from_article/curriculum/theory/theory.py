from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx
from app.domain.course_build import CourseBuildStore
from app.domain.course_from_article.curriculum.theory.theory_expand import (
    _await_indexed,
    _expand_one_theory_chapter,
    _theory_parallel_limit,
    _theory_serial_count,
)
from app.domain.course_from_article.curriculum.theory.theory_sections import theory_chapter_digest
from app.domain.course_from_article.quality.chapter_quality import (
    reinforce_theory_chapter,
    theory_content_is_usable,
)
from app.domain.course_from_article.workflow.events.progress import _band_progress, _stage_event
from app.domain.errors import TutorError
from app.domain.llm.content.prose_dedupe import clean_theory_markdown
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest

__all__ = [
    "_await_indexed",
    "_expand_one_theory_chapter",
    "_iter_theory_expansion",
    "_theory_parallel_limit",
    "_theory_serial_count",
]


def _heal_restored_theory(step: dict[str, object]) -> dict[str, object]:
    content = step.get("content")
    if isinstance(content, str) and content.strip():
        return {**step, "content": clean_theory_markdown(content)}
    return step


def _persist_theory(
    store: CourseBuildStore | None,
    *,
    user_id: uuid.UUID | None,
    build_id: uuid.UUID | None,
    chapter_id: str,
    step: dict[str, object],
    done: int,
    chapter_total: int,
    band_theory: tuple[float, float],
    title: str,
) -> None:
    if store is None or user_id is None or build_id is None:
        return
    store.save_theory_step(user_id, build_id, chapter_id, step)
    store.patch_meta(
        user_id,
        build_id,
        stage="theory",
        chapters_done=done,
        chapter_total=chapter_total,
        progress=_band_progress(band_theory, done, chapter_total),
        message=f"Theory ready: {title}",
        clear_error=True,
    )


def _digest_from_step(step: dict[str, object]) -> str:
    return theory_chapter_digest(str(step.get("content") or ""))


def _joined_prior_digests(digests: list[str]) -> str:
    return "\n".join(item for item in digests[-3:] if item)


@dataclass(frozen=True)
class TheoryExpansionRun:
    client: httpx.AsyncClient
    target: object
    body: CourseFromArticleRequest
    compact: bool
    chapters: list[dict[str, str]]
    outcomes: list[str]
    book_spine: dict[str, str]
    band_theory: tuple[float, float]
    store: CourseBuildStore | None
    user_id: uuid.UUID | None
    build_id: uuid.UUID | None
    sectional: bool
    max_continues: int | None
    sentences_per_window: int | None
    quality_rounds: int
    quality_notes: list[str]


@dataclass
class TheoryProgress:
    done: int = 0
    prior_digests: list[str] = field(default_factory=list)


def _load_saved_theory(run: TheoryExpansionRun) -> dict[str, dict[str, object]]:
    saved: dict[str, dict[str, object]] = {}
    if run.store is None or run.user_id is None or run.build_id is None:
        return saved
    for chapter in run.chapters:
        loaded = run.store.load_theory_steps(run.user_id, run.build_id, [chapter["id"]])
        if loaded:
            healed = _heal_restored_theory(loaded[0])
            if theory_content_is_usable(healed.get("content")):
                saved[chapter["id"]] = healed
    return saved


def _theory_step_from_event(event: dict[str, object]) -> dict[str, object] | None:
    if "_theory_step" not in event:
        return None
    step = event["_theory_step"]
    if not isinstance(step, dict):
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course theory stage missing chapter")
    return step


async def _iter_one_chapter(
    run: TheoryExpansionRun,
    *,
    chapter: dict[str, str],
    index: int,
    progress: TheoryProgress,
) -> AsyncIterator[dict[str, object]]:
    async for event in _run_one_chapter(
        run.client,
        run.target,
        body=run.body,
        compact=run.compact,
        chapter=chapter,
        chapters=run.chapters,
        outcomes=run.outcomes,
        book_spine=run.book_spine,
        index=index,
        chapter_total=len(run.chapters),
        done=progress.done,
        band_theory=run.band_theory,
        sectional=run.sectional,
        max_continues=run.max_continues,
        sentences_per_window=run.sentences_per_window,
        prior_chapter_digest=_joined_prior_digests(progress.prior_digests),
        store=run.store,
        user_id=run.user_id,
        build_id=run.build_id,
        quality_rounds=run.quality_rounds,
        quality_notes=run.quality_notes,
    ):
        yield event


async def _iter_restored_theory(
    run: TheoryExpansionRun,
    *,
    saved: dict[str, dict[str, object]],
    theory_steps: list[dict[str, object]],
) -> AsyncIterator[dict[str, object]]:
    generated: dict[str, dict[str, object]] = dict(saved)
    progress = TheoryProgress()
    for index, chapter in enumerate(run.chapters):
        chapter_id = chapter["id"]
        if chapter_id in saved:
            progress.done += 1
            progress.prior_digests.append(_digest_from_step(saved[chapter_id]))
            yield _stage_event(
                stage="theory",
                status="done",
                progress=_band_progress(run.band_theory, progress.done, len(run.chapters)),
                message=f"Theory restored: {chapter['title']}",
                message_key="theoryRestored",
                message_params={"title": chapter["title"]},
                index=index + 1,
                total=len(run.chapters),
                detail={"chapter_id": chapter_id, "restored": True},
            )
            continue
        async for event in _iter_one_chapter(
            run,
            chapter=chapter,
            index=index,
            progress=progress,
        ):
            step = _theory_step_from_event(event)
            if step is None:
                yield event
                continue
            generated[chapter_id] = step
            progress.prior_digests.append(_digest_from_step(step))
            progress.done += 1
    theory_steps.extend(generated[chapter["id"]] for chapter in run.chapters)


async def _iter_serial_theory(
    run: TheoryExpansionRun,
    *,
    indexed_chapters: list[tuple[int, dict[str, str]]],
    theory_steps: list[dict[str, object]],
    progress: TheoryProgress,
) -> AsyncIterator[dict[str, object]]:
    for index, chapter in indexed_chapters:
        async for event in _iter_one_chapter(
            run,
            chapter=chapter,
            index=index,
            progress=progress,
        ):
            step = _theory_step_from_event(event)
            if step is None:
                yield event
                continue
            theory_steps.append(step)
            progress.prior_digests.append(_digest_from_step(step))
            progress.done += 1


async def _expand_parallel_chapter(
    run: TheoryExpansionRun,
    *,
    index: int,
    chapter: dict[str, str],
    semaphore: asyncio.Semaphore,
) -> dict[str, object]:
    step = await _expand_one_theory_chapter(
        run.client,
        run.target,
        body=run.body,
        compact=run.compact,
        chapter=chapter,
        chapters=run.chapters,
        outcomes=run.outcomes,
        book_spine=run.book_spine,
        index=index,
        semaphore=semaphore,
        max_continues=run.max_continues,
        sectional=False,
        prior_chapter_digest="",
    )
    if run.quality_rounds <= 0:
        return step
    reinforced, notes = await reinforce_theory_chapter(
        run.client,
        run.target,
        body=run.body,
        chapter=chapter,
        step=step,
        outcomes=run.outcomes,
        max_rounds=run.quality_rounds,
        compact=run.compact,
    )
    run.quality_notes.extend(notes)
    return reinforced


async def _iter_parallel_theory(
    run: TheoryExpansionRun,
    *,
    remaining: list[tuple[int, dict[str, str]]],
    theory_steps: list[dict[str, object]],
    progress: TheoryProgress,
    limit: int,
) -> AsyncIterator[dict[str, object]]:
    chapter_total = len(run.chapters)
    for index, chapter in remaining:
        yield _stage_event(
            stage="theory",
            status="running",
            progress=_band_progress(run.band_theory, progress.done, chapter_total),
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
            _expand_parallel_chapter(run, index=index, chapter=chapter, semaphore=semaphore)
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
        progress.done += 1
        _persist_theory(
            run.store,
            user_id=run.user_id,
            build_id=run.build_id,
            chapter_id=chapter["id"],
            step=step,
            done=progress.done,
            chapter_total=chapter_total,
            band_theory=run.band_theory,
            title=str(step.get("title") or chapter["title"]),
        )
        yield _stage_event(
            stage="theory",
            status="done",
            progress=_band_progress(run.band_theory, progress.done, chapter_total),
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
    store: CourseBuildStore | None = None,
    user_id: uuid.UUID | None = None,
    build_id: uuid.UUID | None = None,
    sectional: bool = False,
    max_continues: int | None = None,
    sentences_per_window: int | None = None,
    quality_rounds: int = 0,
    warnings: list[str] | None = None,
) -> AsyncIterator[dict[str, object]]:
    run = TheoryExpansionRun(
        client=client,
        target=target,
        body=body,
        compact=compact,
        chapters=chapters,
        outcomes=outcomes,
        book_spine=book_spine,
        band_theory=band_theory,
        store=store,
        user_id=user_id,
        build_id=build_id,
        sectional=sectional,
        max_continues=max_continues,
        sentences_per_window=sentences_per_window,
        quality_rounds=quality_rounds,
        quality_notes=warnings if warnings is not None else [],
    )
    saved = _load_saved_theory(run)
    if saved:
        async for event in _iter_restored_theory(run, saved=saved, theory_steps=theory_steps):
            yield event
        return
    serial_n = _theory_serial_count(len(chapters), compact=compact, sectional=sectional)
    progress = TheoryProgress()
    indexed = list(enumerate(chapters))
    async for event in _iter_serial_theory(
        run,
        indexed_chapters=indexed[:serial_n],
        theory_steps=theory_steps,
        progress=progress,
    ):
        yield event
    remaining = indexed[serial_n:]
    if not remaining:
        return
    limit = _theory_parallel_limit(compact=compact, sectional=sectional)
    if limit <= 1 or len(remaining) == 1:
        async for event in _iter_serial_theory(
            run,
            indexed_chapters=remaining,
            theory_steps=theory_steps,
            progress=progress,
        ):
            yield event
        return
    async for event in _iter_parallel_theory(
        run,
        remaining=remaining,
        theory_steps=theory_steps,
        progress=progress,
        limit=limit,
    ):
        yield event


async def _reinforce_chapter(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapter: dict[str, str],
    outcomes: list[str],
    step: dict[str, object],
    quality_rounds: int,
    quality_notes: list[str],
) -> dict[str, object]:
    reinforced, notes = await reinforce_theory_chapter(
        client,
        target,
        body=body,
        chapter=chapter,
        step=step,
        outcomes=outcomes,
        max_rounds=quality_rounds,
        compact=compact,
    )
    quality_notes.extend(notes)
    return reinforced


def _chapter_progress_event(
    *,
    chapter: dict[str, str],
    index: int,
    chapter_total: int,
    done: int,
    band_theory: tuple[float, float],
    mode: str,
) -> dict[str, object]:
    return _stage_event(
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
            "mode": mode,
        },
    )


def _chapter_done_event(
    *,
    chapter: dict[str, str],
    step: dict[str, object],
    index: int,
    chapter_total: int,
    done: int,
    band_theory: tuple[float, float],
    mode: str,
) -> dict[str, object]:
    return _stage_event(
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
            "mode": mode,
        },
    )


def _quality_progress_event(
    *,
    chapter: dict[str, str],
    index: int,
    chapter_total: int,
    done: int,
    band_theory: tuple[float, float],
    quality_rounds: int,
) -> dict[str, object]:
    return _stage_event(
        stage="theory",
        status="running",
        progress=_band_progress(band_theory, done, chapter_total),
        message=f"Quality reinforce: {chapter['title']}",
        message_key="theoryQuality",
        message_params={"title": chapter["title"]},
        index=index + 1,
        total=chapter_total,
        detail={
            "chapter_id": chapter["id"],
            "mode": "quality",
            "rounds": quality_rounds,
        },
    )


def _section_progress_event(
    *,
    chapter: dict[str, str],
    index: int,
    chapter_total: int,
    done: int,
    band_theory: tuple[float, float],
    section_index: int,
    section_count: int,
) -> dict[str, object]:
    return _stage_event(
        stage="theory",
        status="running",
        progress=_band_progress(band_theory, done, chapter_total),
        message=f"Expanding chapter section {section_index}/{section_count}: {chapter['title']}",
        message_key="theoryExpanding",
        message_params={"title": chapter["title"]},
        index=index + 1,
        total=chapter_total,
        detail={
            "chapter_id": chapter["id"],
            "chapter_title": chapter["title"],
            "mode": "sectional",
            "section_index": section_index,
            "section_count": section_count,
        },
    )


async def _run_one_chapter(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapter: dict[str, str],
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    index: int,
    chapter_total: int,
    done: int,
    band_theory: tuple[float, float],
    sectional: bool,
    max_continues: int | None,
    sentences_per_window: int | None,
    prior_chapter_digest: str,
    store: CourseBuildStore | None,
    user_id: uuid.UUID | None,
    build_id: uuid.UUID | None,
    quality_rounds: int = 0,
    quality_notes: list[str] | None = None,
) -> AsyncIterator[dict[str, object]]:
    mode = "sectional" if sectional else "serial"
    notes = quality_notes if quality_notes is not None else []
    yield _chapter_progress_event(
        chapter=chapter,
        index=index,
        chapter_total=chapter_total,
        done=done,
        band_theory=band_theory,
        mode=mode,
    )

    section_events: list[dict[str, object]] = []

    async def on_section(section_index: int, section_count: int) -> None:
        section_events.append(
            _section_progress_event(
                chapter=chapter,
                index=index,
                chapter_total=chapter_total,
                done=done,
                band_theory=band_theory,
                section_index=section_index,
                section_count=section_count,
            )
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
        max_continues=max_continues,
        sectional=sectional,
        sentences_per_window=sentences_per_window,
        prior_chapter_digest=prior_chapter_digest,
        on_section=on_section if sectional else None,
    )
    for event in section_events:
        yield event

    if quality_rounds > 0:
        yield _quality_progress_event(
            chapter=chapter,
            index=index,
            chapter_total=chapter_total,
            done=done,
            band_theory=band_theory,
            quality_rounds=quality_rounds,
        )
        step = await _reinforce_chapter(
            client,
            target,
            body=body,
            compact=compact,
            chapter=chapter,
            step=step,
            outcomes=outcomes,
            quality_rounds=quality_rounds,
            quality_notes=notes,
        )

    next_done = done + 1
    _persist_theory(
        store,
        user_id=user_id,
        build_id=build_id,
        chapter_id=chapter["id"],
        step=step,
        done=next_done,
        chapter_total=chapter_total,
        band_theory=band_theory,
        title=str(step.get("title") or chapter["title"]),
    )
    yield _chapter_done_event(
        chapter=chapter,
        step=step,
        index=index,
        chapter_total=chapter_total,
        done=next_done,
        band_theory=band_theory,
        mode=mode,
    )
    yield {"_theory_step": step}
