from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import httpx
from app.domain.course_from_article.common.content.constants import (
    _THEORY_PARALLEL_LIMIT,
    _THEORY_SERIAL_PREFIX,
)
from app.domain.course_from_article.common.content.messages import (
    _theory_content_user_message,
    _theory_meta_user_message,
    _theory_section_user_message,
)
from app.domain.course_from_article.common.content.normalize import _normalize_theory_step
from app.domain.course_from_article.common.runtime.course_context import get_course_profile
from app.domain.course_from_article.common.runtime.llm_limits import COURSE_LLM
from app.domain.course_from_article.common.runtime.stage_llm import _stage_json
from app.domain.course_from_article.curriculum.outline.course_locale import (
    course_language_name,
    normalize_course_locale,
)
from app.domain.course_from_article.curriculum.theory.theory_sections import (
    align_section_cache,
    pack_sentence_windows,
    split_theory_excerpt,
    stitch_theory_sections,
    theory_chapter_digest,
)
from app.domain.llm import LlmTarget, complete_text_until_done
from app.domain.llm.content.prose_dedupe import clean_theory_markdown
from app.domain.llm.transport.request import looks_like_ollama_endpoint
from app.domain.ollama.defaults import num_ctx_for_compact
from app.domain.ollama.quality_lang import needs_quality_retry
from app.domain.prompt_compose import course_from_article_theory_prose_prompt
from studio_contracts.api.studio_schemas import CourseFromArticleRequest

_REWRITE_SYSTEM = (
    "You rewrite a theory chapter into the required course language. "
    "Keep the same teaching content and markdown structure. "
    "Plain markdown only — no JSON, no preamble. "
    "Code fences and identifiers stay unchanged; rewrite all surrounding prose. "
    "Remove duplicated sections if the draft repeats itself. "
    "For Russian: fix transliteration mashups "
    "(Комputer→компьютерное, видаении→видении) into correct spelling."
)

SectionProgressHook = Callable[[int, int], Awaitable[None]]
LoadSectionDrafts = Callable[[], list[str]]
SaveSectionDraft = Callable[[int, int, str], None]


def _theory_serial_count(chapter_count: int, *, compact: bool, sectional: bool = False) -> int:
    if chapter_count <= 0:
        return 0
    if sectional or compact or chapter_count <= _THEORY_SERIAL_PREFIX:
        return chapter_count
    return _THEORY_SERIAL_PREFIX


def _theory_parallel_limit(*, compact: bool, sectional: bool = False) -> int:
    return 1 if sectional or compact else _THEORY_PARALLEL_LIMIT


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
        max_tokens=COURSE_LLM.theory_max_tokens,
        max_continues=2 if num_ctx else 4,
        temperature=0.1,
        top_p=0.9 if num_ctx else None,
        num_ctx=num_ctx,
    )
    cleaned = rewritten.strip()
    if cleaned and not needs_quality_retry(cleaned, locale):
        return cleaned
    return cleaned or draft


def _theory_content_system(*, compact: bool, local_runtime: bool = False) -> str:
    from app.domain.course_from_article.common.runtime.course_context import get_strategy_pack

    return course_from_article_theory_prose_prompt(
        compact=compact,
        course_profile=get_course_profile(),
        local_runtime=local_runtime,
        strategy_pack=get_strategy_pack(),
    )


def _clean_theory_prose(content: str) -> str:
    return clean_theory_markdown(content)


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
    max_continues: int | None = None,
    sectional: bool = False,
    prior_chapter_digest: str = "",
    on_section: SectionProgressHook | None = None,
    sentences_per_window: int | None = None,
    load_section_drafts: LoadSectionDrafts | None = None,
    save_section_draft: SaveSectionDraft | None = None,
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
                max_continues=max_continues,
                prior_chapter_digest=prior_chapter_digest,
            )
        if sectional:
            return await _expand_theory_sectional(
                client,
                target,
                body=body,
                chapter=chapter,
                chapters=chapters,
                outcomes=outcomes,
                book_spine=book_spine,
                index=index,
                max_continues=max_continues,
                prior_chapter_digest=prior_chapter_digest,
                on_section=on_section,
                sentences_per_window=sentences_per_window,
                load_section_drafts=load_section_drafts,
                save_section_draft=save_section_draft,
            )
        return await _expand_theory_full(
            client,
            target,
            body=body,
            chapter=chapter,
            chapters=chapters,
            outcomes=outcomes,
            book_spine=book_spine,
            index=index,
            max_continues=max_continues,
            prior_chapter_digest=prior_chapter_digest,
        )

    if semaphore is None:
        return await _run()
    async with semaphore:
        return await _run()


async def _expand_theory_full(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    index: int,
    max_continues: int | None = None,
    prior_chapter_digest: str = "",
) -> dict[str, object]:
    meta = await _stage_json(
        client,
        target,
        compact=False,
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
    if not isinstance(target, LlmTarget):
        msg = "theory content generation requires an LLM target"
        raise TypeError(msg)
    continues = 3 if max_continues is None else max(0, max_continues)
    content = await complete_text_until_done(
        client,
        target,
        system_prompt=_theory_content_system(
            compact=False,
            local_runtime=looks_like_ollama_endpoint(target),
        ),
        user_message=_theory_content_user_message(
            chapter,
            body,
            outcomes,
            chapters=chapters,
            index=index,
            book_spine=book_spine,
            title=_as_meta_title(meta, chapter),
            prior_chapter_digest=prior_chapter_digest,
        ),
        max_tokens=COURSE_LLM.theory_max_tokens,
        max_continues=continues,
        temperature=COURSE_LLM.theory_temperature,
        top_p=None,
        num_ctx=target.num_ctx,
    )
    content = await _ensure_theory_locale(
        client, target, body=body, content=content, num_ctx=target.num_ctx
    )
    content = _clean_theory_prose(content)
    payload = {
        **meta,
        "id": meta.get("id") or chapter["id"],
        "kind": "theory",
        "title": _as_meta_title(meta, chapter),
        "content": content,
    }
    return _normalize_theory_step(payload, chapter)


async def _expand_theory_sectional(
    client: httpx.AsyncClient,
    target: object,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    index: int,
    max_continues: int | None = None,
    prior_chapter_digest: str = "",
    on_section: SectionProgressHook | None = None,
    sentences_per_window: int | None = None,
    load_section_drafts: LoadSectionDrafts | None = None,
    save_section_draft: SaveSectionDraft | None = None,
) -> dict[str, object]:
    if not isinstance(target, LlmTarget):
        msg = "theory content generation requires an LLM target"
        raise TypeError(msg)
    excerpt = chapter.get("source_excerpt") or ""
    if sentences_per_window is not None:
        sections = pack_sentence_windows(excerpt, sentences_per_window=sentences_per_window)
    else:
        sections = split_theory_excerpt(excerpt)
    if len(sections) <= 1:
        return await _expand_theory_full(
            client,
            target,
            body=body,
            chapter=chapter,
            chapters=chapters,
            outcomes=outcomes,
            book_spine=book_spine,
            index=index,
            max_continues=max_continues,
            prior_chapter_digest=prior_chapter_digest,
        )

    continues = 1 if max_continues is None else min(1, max(0, max_continues))
    cached = align_section_cache(
        load_section_drafts() if load_section_drafts is not None else [],
        len(sections),
    )
    drafts = await _sectional_window_drafts(
        client,
        target,
        body=body,
        chapter=chapter,
        chapters=chapters,
        outcomes=outcomes,
        book_spine=book_spine,
        index=index,
        sections=sections,
        cached=cached,
        continues=continues,
        prior_chapter_digest=prior_chapter_digest,
        on_section=on_section,
        save_section_draft=save_section_draft,
    )

    content = _clean_theory_prose(stitch_theory_sections(drafts))
    payload = {
        "id": chapter["id"],
        "kind": "theory",
        "title": chapter["title"],
        "content": content,
    }
    return _normalize_theory_step(payload, chapter)


async def _sectional_window_drafts(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    chapters: list[dict[str, str]],
    outcomes: list[str],
    book_spine: dict[str, str],
    index: int,
    sections: list[str],
    cached: list[str],
    continues: int,
    prior_chapter_digest: str,
    on_section: SectionProgressHook | None,
    save_section_draft: SaveSectionDraft | None,
) -> list[str]:
    drafts: list[str] = []
    running_summary = ""
    section_total = len(sections)
    for section_index, section_excerpt in enumerate(sections, start=1):
        if on_section is not None:
            await on_section(section_index, section_total)
        ready = cached[section_index - 1] if section_index <= len(cached) else ""
        if ready.strip():
            cleaned = _clean_theory_prose(ready)
            drafts.append(cleaned)
            running_summary = theory_chapter_digest(cleaned, max_chars=280)
            continue
        draft = await complete_text_until_done(
            client,
            target,
            system_prompt=_theory_content_system(
                compact=False,
                local_runtime=looks_like_ollama_endpoint(target),
            ),
            user_message=_theory_section_user_message(
                chapter,
                body,
                outcomes,
                chapters=chapters,
                index=index,
                section_excerpt=section_excerpt,
                section_index=section_index,
                section_count=section_total,
                section_running_summary=running_summary,
                prior_chapter_digest=prior_chapter_digest,
                book_spine=book_spine,
            ),
            max_tokens=COURSE_LLM.theory_section_max_tokens,
            max_continues=continues,
            temperature=COURSE_LLM.theory_temperature,
            top_p=0.9,
            num_ctx=target.num_ctx,
        )
        cleaned = _clean_theory_prose(draft)
        drafts.append(cleaned)
        if save_section_draft is not None:
            save_section_draft(section_index, section_total, cleaned)
        running_summary = theory_chapter_digest(cleaned, max_chars=280)
    return drafts


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
    max_continues: int | None = None,
    prior_chapter_digest: str = "",
) -> dict[str, object]:
    if not isinstance(target, LlmTarget):
        msg = "theory content generation requires an LLM target"
        raise TypeError(msg)
    title = chapter["title"]
    from app.config import load_config

    num_ctx = target.num_ctx
    if num_ctx is None and looks_like_ollama_endpoint(target):
        num_ctx = num_ctx_for_compact(load_config(), compact=True)
    continues = 2 if max_continues is None else max(0, max_continues)
    content = await complete_text_until_done(
        client,
        target,
        system_prompt=_theory_content_system(
            compact=True,
            local_runtime=looks_like_ollama_endpoint(target),
        ),
        user_message=_theory_content_user_message(
            chapter,
            body,
            outcomes,
            chapters=chapters,
            index=index,
            book_spine=book_spine,
            title=title,
            compact=True,
            prior_chapter_digest=prior_chapter_digest,
        ),
        max_tokens=3600,
        max_continues=continues,
        temperature=0.15,
        top_p=0.85,
        num_ctx=num_ctx,
    )
    content = _clean_theory_prose(content)
    content = await _ensure_theory_locale(
        client, target, body=body, content=content, num_ctx=num_ctx
    )
    content = _clean_theory_prose(content)
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
