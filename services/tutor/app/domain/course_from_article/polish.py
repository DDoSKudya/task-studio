from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from app.domain.errors import TutorError
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .messages import _polish_one_user_message
from .polish_edits import (
    _apply_book_polish_edits,
    _apply_opening_edit,
    _chapter_opening,
    _polish_full_content_ok,
)
from .progress import _stage_event
from .stage_llm import _stage_json

__all__ = [
    "_apply_book_polish_edits",
    "_apply_opening_edit",
    "_chapter_opening",
    "_iter_book_polish",
    "_polish_full_content_ok",
]


async def _iter_book_polish(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    compact: bool,
    chapters: list[dict[str, str]],
    book_spine: dict[str, str],
    band_polish: tuple[float, float],
    theory_steps: list[dict[str, object]],
    warnings: list[str],
) -> AsyncIterator[dict[str, object]]:
    yield _stage_event(
        stage="polish",
        status="running",
        progress=band_polish[0],
        message="Polishing theory into one book voice",
        message_key="polishRunning",
        detail={"chapter_count": len(theory_steps)},
    )
    opening_limit = 520 if compact else 720
    digests: list[dict[str, object]] = []
    for step in theory_steps:
        step_id = str(step.get("id") or "").strip()
        if not step_id:
            continue
        opening, cut = _chapter_opening(str(step.get("content") or ""), opening_limit)
        digests.append(
            {
                "id": step_id,
                "title": str(step.get("title") or ""),
                "opening": opening,
                "opening_chars": cut,
                "content_chars": len(str(step.get("content") or "")),
            }
        )
    applied = 0
    for index, digest in enumerate(digests):
        try:
            payload = await _stage_json(
                client,
                target,
                compact=compact,
                stage="polish",
                user_message=_polish_one_user_message(
                    body,
                    chapters=chapters,
                    book_spine=book_spine,
                    digest=digest,
                    index=index,
                    total=len(digests),
                ),
                max_tokens=1400 if compact else 2400,
            )
            applied += _apply_book_polish_edits(theory_steps, payload, [digest])
        except TutorError as exc:
            warnings.append(f"book polish skipped for {digest['id']}: {exc.detail}")
    yield _stage_event(
        stage="polish",
        status="done",
        progress=band_polish[1],
        message=f"Book polish applied to {applied} chapter(s)",
        message_key="polishDone",
        message_params={"count": applied},
        detail={"edits_applied": applied, "chapter_count": len(theory_steps)},
    )
