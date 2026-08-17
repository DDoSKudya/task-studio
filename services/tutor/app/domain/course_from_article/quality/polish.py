from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
from app.domain.course_from_article.common.content.messages import _polish_one_user_message
from app.domain.course_from_article.common.runtime.llm_limits import COURSE_LLM
from app.domain.course_from_article.common.runtime.stage_llm import _stage_json
from app.domain.course_from_article.quality.polish_edits import (
    _apply_book_polish_edits,
    _apply_opening_edit,
    _chapter_opening,
    _polish_full_content_ok,
)
from app.domain.course_from_article.workflow.events.progress import _stage_event
from app.domain.errors import TutorError
from studio_contracts.api.studio_schemas import CourseFromArticleRequest

__all__ = [
    "_apply_book_polish_edits",
    "_apply_opening_edit",
    "_chapter_opening",
    "_iter_book_polish",
    "_is_llm_capacity_error",
    "_polish_attempt_settings",
    "_polish_full_content_ok",
    "_polish_skip_warning",
]

_POLISH_ATTEMPTS = 3


def _is_llm_capacity_error(detail: str) -> bool:
    lower = detail.casefold()
    return any(
        marker in lower
        for marker in (
            "request_tier_capacity_exceeded",
            "service tier capacity exceeded",
            'raw_status_code":429',
            "raw_status_code':429",
            '"code":"3505"',
            '"code": 3505',
        )
    ) or ("429" in lower and "capacity" in lower)


def _polish_skip_warning(step_id: str, detail: str) -> str:
    if _is_llm_capacity_error(detail):
        return f"book polish skipped capacity: {step_id}"
    short = " ".join(detail.split())
    if len(short) > 160:
        short = f"{short[:160]}…"
    return f"book polish skipped for {step_id}: {short}"


def _polish_attempt_settings(*, compact: bool, attempt: int) -> tuple[bool, int]:
    if compact:
        if attempt <= 1:
            return True, 1400
        elif attempt == 2:
            return True, 1150
        else:
            return True, 900

    return False, COURSE_LLM.polish_max_tokens


async def _polish_digest_with_attempts(
    *,
    client: httpx.AsyncClient,
    target: object,
    body: CourseFromArticleRequest,
    chapters: list[dict[str, str]],
    book_spine: dict[str, str],
    digest: dict[str, object],
    index: int,
    total: int,
    compact: bool,
    theory_steps: list[dict[str, object]],
) -> tuple[int, TutorError | None]:
    applied = 0
    last_error: TutorError | None = None
    for attempt in range(1, _POLISH_ATTEMPTS + 1):
        attempt_compact, max_tokens = _polish_attempt_settings(compact=compact, attempt=attempt)
        try:
            payload = await _stage_json(
                client,
                target,
                compact=attempt_compact,
                stage="polish",
                user_message=_polish_one_user_message(
                    body,
                    chapters=chapters,
                    book_spine=book_spine,
                    digest=digest,
                    index=index,
                    total=total,
                ),
                max_tokens=max_tokens,
            )
            applied += _apply_book_polish_edits(theory_steps, payload, [digest])
            last_error = None
            break
        except TutorError as exc:
            last_error = exc
            if attempt >= _POLISH_ATTEMPTS:
                break
            await asyncio.sleep(min(3.0, 0.8 * (2 ** (attempt - 1))))
    return applied, last_error


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
        applied_count, last_error = await _polish_digest_with_attempts(
            client=client,
            target=target,
            body=body,
            chapters=chapters,
            book_spine=book_spine,
            digest=digest,
            index=index,
            total=len(digests),
            compact=compact,
            theory_steps=theory_steps,
        )
        if last_error is not None:
            raise last_error
        applied += applied_count

    yield _stage_event(
        stage="polish",
        status="done",
        progress=band_polish[1],
        message=f"Book polish applied to {applied} chapter(s)",
        message_key="polishDone",
        message_params={"count": applied},
        detail={
            "edits_applied": applied,
            "chapter_count": len(theory_steps),
        },
    )
