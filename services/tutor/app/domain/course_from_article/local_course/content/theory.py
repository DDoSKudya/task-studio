from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import NoReturn

import httpx
from app.domain.course_build import CourseBuildStore
from app.domain.course_from_article.common.runtime.llm_limits import COURSE_LLM
from app.domain.course_from_article.curriculum.outline.course_locale import (
    course_language_name,
    normalize_course_locale,
)
from app.domain.course_from_article.curriculum.outline.normalize_outline import (
    _normalize_theory_step,
)
from app.domain.course_from_article.curriculum.theory.theory_sections import (
    align_section_cache,
    pack_sentence_windows,
    stitch_theory_sections,
    theory_chapter_digest,
)
from app.domain.course_from_article.local_course.content.messages import (
    theory_patch_user_message,
    theory_system_prompt,
    theory_window_user_message,
)
from app.domain.course_from_article.local_course.policy.heuristics import theory_copies_excerpt
from app.domain.course_from_article.local_course.policy.policy import LocalCoursePolicy
from app.domain.course_from_article.quality.chapter_quality import (
    _heuristic_critique,
    theory_content_is_usable,
)
from app.domain.course_strategies import (
    ensure_figures_in_theory,
    ensure_mermaid_from_visual_plan,
    montage_theory_from_excerpt,
)
from app.domain.course_strategies.blueprint import build_chapter_blueprint
from app.domain.errors import TutorError
from app.domain.llm import complete_text_until_done
from app.domain.llm.content.prose_dedupe import clean_theory_markdown
from app.domain.llm.target import LlmTarget
from app.domain.ollama.quality_lang import (
    ReplyLanguage,
    language_mismatch,
    needs_quality_retry,
    repair_script_mixing,
)
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


def _chapter_label(chapter: dict[str, str]) -> str:
    return str(chapter.get("title") or chapter.get("id") or "chapter")


def _fail_local_theory(
    chapter: dict[str, str], reason: str, *, cause: BaseException | None = None
) -> NoReturn:
    message = f"local theory failed for «{_chapter_label(chapter)}»: {reason}"
    if cause is None:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, message)
    raise TutorError(status.HTTP_502_BAD_GATEWAY, message) from cause


def _windows_for_chapter(chapter: dict[str, str], *, sentences_per_window: int) -> list[str]:
    excerpt = (chapter.get("source_excerpt") or "").strip()
    title = (chapter.get("title") or "").strip()
    if not excerpt or excerpt.casefold() == title.casefold():
        return []

    windows = pack_sentence_windows(
        excerpt,
        sentences_per_window=sentences_per_window,
        max_windows=8,
    )
    if len(windows) > 8:
        merged: list[str] = []
        start = 0
        total = len(windows)
        for bucket in range(8):
            left = 8 - bucket
            take = max(1, (total - start + left - 1) // left)
            merged.append(" ".join(windows[start : start + take]))
            start += take
            if start >= total:
                break
        windows = merged
    return windows or [excerpt]


async def _write_window(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    excerpt: str,
    window_index: int,
    window_count: int,
    prior_digest: str,
    continues: int,
    attempts: int = 1,
    max_tokens: int,
    book_spine: dict[str, str] | None = None,
    next_title: str = "",
) -> str:
    last_exc: BaseException | None = None
    for _ in range(max(1, attempts)):
        try:
            draft = await complete_text_until_done(
                client,
                target,
                system_prompt=theory_system_prompt(body.locale or "ru"),
                user_message=theory_window_user_message(
                    locale=body.locale or "ru",
                    title=chapter["title"],
                    objective=chapter.get("objective") or "",
                    excerpt=excerpt,
                    window_index=window_index,
                    window_count=window_count,
                    prior_digest=prior_digest,
                    book_spine=book_spine,
                    next_title=next_title,
                ),
                max_tokens=max_tokens,
                max_continues=continues,
                temperature=COURSE_LLM.theory_temperature,
                top_p=0.9,
                num_ctx=target.num_ctx,
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            last_exc = exc
            continue
        cleaned = clean_theory_markdown(draft)
        if cleaned.strip():
            return cleaned
    if last_exc is not None:
        _fail_local_theory(
            chapter,
            f"window {window_index}/{window_count} LLM error",
            cause=last_exc,
        )
    _fail_local_theory(chapter, f"window {window_index}/{window_count} returned empty prose")


async def _patch_theory(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    content: str,
    rounds: int,
    max_tokens: int,
    source_excerpt: str | None = None,
) -> str:
    draft = content
    excerpt = (
        source_excerpt
        if source_excerpt is not None
        else (chapter.get("source_excerpt") or "").strip()
    )
    critique_chapter = {**chapter, "source_excerpt": excerpt}
    locale = normalize_course_locale(body.locale)
    for _ in range(max(0, rounds)):
        critique = _heuristic_critique(critique_chapter, draft)
        lang_bad = needs_quality_retry(draft, locale)
        if critique.ok and not lang_bad:
            return draft
        must_fix = list(critique.must_fix or critique.issues)
        if lang_bad:
            must_fix.insert(
                0,
                f"Rewrite ALL teaching prose in {course_language_name(locale)} ({locale}) only",
            )
        try:
            patched = await complete_text_until_done(
                client,
                target,
                system_prompt=theory_system_prompt(locale),
                user_message=theory_patch_user_message(
                    locale=locale,
                    title=chapter["title"],
                    excerpt=excerpt,
                    draft=draft,
                    must_fix=must_fix,
                ),
                max_tokens=max_tokens,
                max_continues=COURSE_LLM.theory_patch_continues,
                temperature=COURSE_LLM.theory_patch_temperature,
                top_p=0.9,
                num_ctx=target.num_ctx,
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            _fail_local_theory(chapter, "quality patch failed", cause=exc)
        if cleaned := clean_theory_markdown(patched.strip() or draft):
            draft = cleaned
    return draft


def _cached_sections(
    store: CourseBuildStore | None,
    *,
    user_id: uuid.UUID | None,
    build_id: uuid.UUID | None,
    chapter_id: str,
    count: int,
) -> list[str]:
    if store is None or user_id is None or build_id is None:
        return []
    return align_section_cache(
        store.load_section_drafts(user_id, build_id, chapter_id),
        count,
    )


async def _expand_theory_sections(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    policy: LocalCoursePolicy,
    windows: list[str],
    cached: list[str],
    prior_chapter_digest: str,
    book_spine: dict[str, str] | None,
    next_title: str,
    store: CourseBuildStore | None,
    user_id: uuid.UUID | None,
    build_id: uuid.UUID | None,
) -> list[str]:
    drafts: list[str] = []
    running = prior_chapter_digest
    for index, window in enumerate(windows, start=1):
        ready = cached[index - 1] if index <= len(cached) else ""
        if ready.strip() and not needs_quality_retry(ready, normalize_course_locale(body.locale)):
            cleaned = clean_theory_markdown(ready)
        else:
            cleaned = await _write_window(
                client,
                target,
                body=body,
                chapter=chapter,
                excerpt=window,
                window_index=index,
                window_count=len(windows),
                prior_digest=running,
                continues=max(0, policy.theory_max_continues),
                attempts=policy.topic_retries + 1,
                max_tokens=policy.theory_section_max_tokens,
                book_spine=book_spine,
                next_title=next_title,
            )
            cleaned = await _patch_theory(
                client,
                target,
                body=body,
                chapter=chapter,
                content=cleaned,
                rounds=policy.section_quality_rounds,
                max_tokens=policy.theory_section_max_tokens,
                source_excerpt=window,
            )
            if store is not None and user_id is not None and build_id is not None:
                store.save_section_draft(
                    user_id,
                    build_id,
                    chapter["id"],
                    index=index,
                    total=len(windows),
                    content=cleaned,
                )
        drafts.append(cleaned)
        running = theory_chapter_digest(cleaned, max_chars=280)
    return drafts


def _add_theory_visuals(
    content: str,
    *,
    chapter: dict[str, str],
    blueprint: Mapping[str, object],
    locale: ReplyLanguage,
) -> str:
    content = ensure_figures_in_theory(content, str(chapter.get("source_images") or ""))
    visual_plan = blueprint.get("visual_plan")
    return ensure_mermaid_from_visual_plan(
        content,
        visual_plan=visual_plan if isinstance(visual_plan, dict) else None,
        title=str(chapter.get("title") or ""),
        key_claims=_blueprint_claims(blueprint),
        locale=locale,
    )


def _blueprint_claims(blueprint: Mapping[str, object]) -> list[str]:
    claims = blueprint.get("key_claims")
    if not isinstance(claims, list):
        return []
    return [str(item) for item in claims if item]


def _language_fallback(
    content: str,
    *,
    chapter: dict[str, str],
    blueprint: Mapping[str, object],
    locale: ReplyLanguage,
) -> str:
    if not language_mismatch(content, locale):
        return content
    fallback = montage_theory_from_excerpt(
        title=str(chapter.get("title") or ""),
        excerpt=(chapter.get("source_excerpt") or "").strip(),
        source_images=str(chapter.get("source_images") or ""),
        locale=locale,
        key_claims=_blueprint_claims(blueprint),
    )
    repaired = repair_script_mixing(clean_theory_markdown(fallback))
    if language_mismatch(repaired, locale) and len(repaired) <= len(content):
        return content
    return _add_theory_visuals(
        repaired,
        chapter=chapter,
        blueprint=blueprint,
        locale=locale,
    )


async def expand_local_theory_chapter(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    policy: LocalCoursePolicy,
    prior_chapter_digest: str = "",
    book_spine: dict[str, str] | None = None,
    next_title: str = "",
    store: CourseBuildStore | None = None,
    user_id: uuid.UUID | None = None,
    build_id: uuid.UUID | None = None,
) -> dict[str, object]:
    chapter_id = chapter["id"]
    locale = normalize_course_locale(body.locale)
    blueprint = build_chapter_blueprint(chapter)
    windows = _windows_for_chapter(chapter, sentences_per_window=policy.sentences_per_window)
    if not windows:
        _fail_local_theory(chapter, "chapter has no source excerpt to teach")

    cached = _cached_sections(
        store,
        user_id=user_id,
        build_id=build_id,
        chapter_id=chapter_id,
        count=len(windows),
    )
    drafts = await _expand_theory_sections(
        client,
        target,
        body=body,
        chapter=chapter,
        policy=policy,
        windows=windows,
        cached=cached,
        prior_chapter_digest=prior_chapter_digest,
        book_spine=book_spine,
        next_title=next_title,
        store=store,
        user_id=user_id,
        build_id=build_id,
    )

    content = await _patch_theory(
        client,
        target,
        body=body,
        chapter=chapter,
        content=clean_theory_markdown(stitch_theory_sections(drafts)),
        rounds=policy.quality_rounds,
        max_tokens=policy.theory_max_tokens,
    )
    content = _add_theory_visuals(
        content,
        chapter=chapter,
        blueprint=blueprint,
        locale=locale,
    )
    excerpt = (chapter.get("source_excerpt") or "").strip()
    if not theory_content_is_usable(content):
        _fail_local_theory(chapter, "theory draft is too thin to teach this chapter")
    if theory_copies_excerpt(content, excerpt):
        _fail_local_theory(chapter, "theory draft copied the excerpt instead of teaching")
    if needs_quality_retry(content, locale):
        content = await _patch_theory(
            client,
            target,
            body=body,
            chapter=chapter,
            content=content,
            rounds=max(1, policy.quality_rounds),
            max_tokens=policy.theory_max_tokens,
        )
    content = repair_script_mixing(clean_theory_markdown(content))
    content = _language_fallback(
        content,
        chapter=chapter,
        blueprint=blueprint,
        locale=locale,
    )
    if language_mismatch(content, locale) and not theory_content_is_usable(content):
        _fail_local_theory(
            chapter,
            f"theory is not in the requested course language ({locale})",
        )
    payload = {
        "id": chapter_id,
        "kind": "theory",
        "title": chapter["title"],
        "content": content,
        "key_claims": blueprint.get("key_claims") or [],
        "visual_plan": blueprint.get("visual_plan") or {},
    }
    return _normalize_theory_step(payload, chapter)
