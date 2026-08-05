from __future__ import annotations

import asyncio

import httpx
from app.domain.llm import LlmTarget, complete_text_until_done
from app.domain.llm.prose_dedupe import collapse_repeated_prose, strip_throat_clearing
from app.domain.ollama.defaults import num_ctx_for_compact
from app.domain.ollama.quality_lang import needs_quality_retry
from studio_contracts.studio_schemas import CourseFromArticleRequest

from .constants import _THEORY_PARALLEL_LIMIT, _THEORY_SERIAL_PREFIX
from .course_locale import course_language_name, normalize_course_locale
from .messages import _theory_content_user_message, _theory_meta_user_message
from .normalize import _normalize_theory_step
from .stage_llm import _stage_json

_CONTENT_SYSTEM = (
    "You write Task Studio theory chapters as plain markdown only. "
    "No JSON, no surrounding fences for the whole chapter, no preamble. "
    "Write the full chapter the learner needs — do not shorten for token limits; "
    "if you run out of space the system will ask you to continue. "
    "Ground every claim in the source excerpt: keep the article's ideas, "
    "examples, and terminology — expand and teach them, do not replace them "
    "with generic filler. "
    "Theory is teaching prose ONLY: never include homework, lab tasks, "
    "numbered assignments, quizzes, 'check yourself', or answer keys — "
    "those belong to later assess/practice stages. "
    "Code samples: one complete ```python (or correct lang) fence per example — "
    "never close the fence mid-class; Markdown outside fences destroys __dunder__ names. "
    "Learner-facing prose must match the request locale."
)

_CONTENT_SYSTEM_COMPACT = (
    "You write Task Studio theory chapters as plain markdown only. "
    "No JSON, no fences around the whole chapter, no preamble. "
    "Teach the chapter thoroughly once: mental model, worked example, traps, short recap. "
    "Never repeat the same section, heading, or paragraph — write each block exactly once. "
    "Do not pad by restarting the chapter. Prefer substance from the source excerpt: "
    "keep the article's core ideas and real examples; do not invent a thinner substitute. "
    "Never include homework, assignments, quizzes, or answer keys in theory. "
    "Code samples: one complete ```python fence per example — never close mid-class; "
    "Markdown outside fences destroys __dunder__ names. "
    "Learner-facing prose must match the request locale. "
    "For Russian locale: use natural Russian terms "
    "(компьютерное зрение, не «Комputer vision» / transliteration mashups). "
    "Keep English only for true identifiers (OpenCV, NumPy, CV as acronym once)."
)

_REWRITE_SYSTEM = (
    "You rewrite a theory chapter into the required course language. "
    "Keep the same teaching content and markdown structure. "
    "Plain markdown only — no JSON, no preamble. "
    "Code fences and identifiers stay unchanged; rewrite all surrounding prose. "
    "Remove duplicated sections if the draft repeats itself. "
    "For Russian: fix transliteration mashups "
    "(Комputer→компьютерное, видаении→видении) into correct spelling."
)


def _theory_serial_count(chapter_count: int, *, compact: bool) -> int:
    if chapter_count <= 0:
        return 0
    if compact or chapter_count <= _THEORY_SERIAL_PREFIX:
        return chapter_count
    return _THEORY_SERIAL_PREFIX


def _theory_parallel_limit(*, compact: bool) -> int:
    return 1 if compact else _THEORY_PARALLEL_LIMIT


async def _ensure_theory_locale(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    content: str,
    num_ctx: int | None,
) -> str:
    locale = normalize_course_locale(body.locale)
    draft = content.strip()
    if not draft or not needs_quality_retry(draft, locale):
        return draft
    name = course_language_name(locale)
    rewritten = await complete_text_until_done(
        client,
        target,
        system_prompt=_REWRITE_SYSTEM,
        user_message=(f"## Required language\n{name} ({locale})\n\n## Draft to rewrite\n{draft}"),
        max_tokens=2200 if num_ctx else 4500,
        max_continues=1 if num_ctx else 4,
        temperature=0.1,
        top_p=0.9 if num_ctx else None,
        num_ctx=num_ctx,
    )
    cleaned = rewritten.strip()
    if cleaned and not needs_quality_retry(cleaned, locale):
        return cleaned
    # Prefer rewritten even if imperfect — unexpected scripts often drop on first pass.
    return cleaned or draft


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
        if compact:
            return await _expand_theory_compact(
                client,
                target,
                body=body,
                chapter=chapter,
                chapters=chapters,
                outcomes=outcomes,
                book_spine=book_spine,
                index=index,
            )
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
            max_tokens=1200,
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
                max_tokens=4500,
                max_continues=8,
                temperature=0.15,
                top_p=None,
                num_ctx=None,
            )
        if not isinstance(target, LlmTarget):
            msg = "theory content generation requires an LLM target"
            raise TypeError(msg)
        content = await _ensure_theory_locale(
            client, target, body=body, content=content, num_ctx=None
        )
        content = collapse_repeated_prose(content)
        content = strip_throat_clearing(content)
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


async def _expand_theory_compact(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    index: int,
) -> dict[str, object]:
    # Local models: one content call beats meta JSON + long continue chain.
    if not isinstance(target, LlmTarget):
        msg = "theory content generation requires an LLM target"
        raise TypeError(msg)
    title = chapter["title"]
    from app.config import load_config

    num_ctx = target.num_ctx
    if num_ctx is None:
        num_ctx = num_ctx_for_compact(load_config(), compact=True)
    content = await complete_text_until_done(
        client,
        target,
        system_prompt=_CONTENT_SYSTEM_COMPACT,
        user_message=_theory_content_user_message(
            chapter,
            body,
            outcomes,
            chapters=chapters,
            index=index,
            book_spine=book_spine,
            title=title,
            compact=True,
        ),
        max_tokens=3600,
        max_continues=2,
        temperature=0.15,
        top_p=0.85,
        num_ctx=num_ctx,
    )
    content = collapse_repeated_prose(content)
    content = await _ensure_theory_locale(
        client, target, body=body, content=content, num_ctx=num_ctx
    )
    content = strip_throat_clearing(collapse_repeated_prose(content))
    payload = {
        "id": chapter["id"],
        "kind": "theory",
        "title": title,
        "content": content,
    }
    return _normalize_theory_step(payload, chapter)


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
