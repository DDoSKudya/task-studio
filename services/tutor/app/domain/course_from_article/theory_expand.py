from __future__ import annotations

import asyncio

import httpx
from app.domain.llm import LlmTarget, complete_text_until_done
from app.domain.ollama.defaults import OLLAMA_NUM_CTX as _OLLAMA_NUM_CTX
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .constants import _THEORY_PARALLEL_LIMIT, _THEORY_SERIAL_PREFIX
from .messages import _theory_content_user_message, _theory_meta_user_message
from .normalize import _normalize_theory_step
from .stage_llm import _stage_json

_CONTENT_SYSTEM = (
    "You write Task Studio theory chapters as plain markdown only. "
    "No JSON, no surrounding fences for the whole chapter, no preamble. "
    "Write the full chapter the learner needs — do not shorten for token limits; "
    "if you run out of space the system will ask you to continue."
)


def _theory_serial_count(chapter_count: int, *, compact: bool) -> int:
    if chapter_count <= 0:
        return 0
    if compact or chapter_count <= _THEORY_SERIAL_PREFIX:
        return chapter_count
    return _THEORY_SERIAL_PREFIX


def _theory_parallel_limit(*, compact: bool) -> int:
    return 1 if compact else _THEORY_PARALLEL_LIMIT


async def _expand_one_theory_chapter(
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
    semaphore: asyncio.Semaphore | None = None,
) -> dict[str, object]:
    async def _run() -> dict[str, object]:
        meta = await _stage_json(
            client,
            target,
            compact=compact,
            stage="theory",
            user_message=_theory_meta_user_message(
                chapter,
                body,
                outcomes,
                chapters=chapters,
                index=index,
                book_spine=book_spine,
            ),
            max_tokens=900 if compact else 1200,
        )
        existing = meta.get("content")

        if isinstance(existing, str) and len(existing.strip()) >= 40:
            content = existing.strip()
        else:
            if not isinstance(target, LlmTarget):
                msg = "theory content generation requires an LLM target"
                raise TypeError(msg)
            content = await complete_text_until_done(
                client,
                target,
                system_prompt=_CONTENT_SYSTEM,
                user_message=_theory_content_user_message(
                    chapter,
                    body,
                    outcomes,
                    chapters=chapters,
                    index=index,
                    book_spine=book_spine,
                    title=_as_meta_title(meta, chapter),
                ),
                max_tokens=2200 if compact else 4500,
                max_continues=4 if compact else 8,
                temperature=0.2 if compact else 0.15,
                top_p=0.9 if compact else None,
                num_ctx=_OLLAMA_NUM_CTX if compact else None,
            )
        payload = {
            **meta,
            "id": meta.get("id") or chapter["id"],
            "kind": "theory",
            "title": _as_meta_title(meta, chapter),
            "content": content,
        }
        return _normalize_theory_step(payload, chapter)

    if semaphore is None:
        return await _run()
    async with semaphore:
        return await _run()


def _as_meta_title(meta: dict[str, object], chapter: dict[str, str]) -> str:
    title = meta.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return chapter["title"]


async def _await_indexed(
    slot: int,
    task: asyncio.Task[dict[str, object]],
) -> tuple[int, dict[str, object]]:
    return slot, await task
