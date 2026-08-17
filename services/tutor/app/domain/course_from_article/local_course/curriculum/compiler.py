from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

import httpx
from app.domain.course_build import CourseBuildMeta, CourseBuildStore
from app.domain.course_from_article.common.content.textutil import _slug
from app.domain.course_from_article.common.runtime.llm_limits import COURSE_LLM
from app.domain.course_from_article.curriculum.outline.chapter_budget import (
    chapter_ceiling,
    chapter_floor,
    corpus_char_count,
)
from app.domain.course_from_article.curriculum.outline.course_locale import (
    catalog_needs_locale_rewrite,
    catalog_text_mismatches_locale,
    locale_line,
    normalize_course_locale,
)
from app.domain.course_from_article.curriculum.outline.normalize_outline import _normalize_domain
from app.domain.course_from_article.local_course.content.messages import (
    order_system_prompt,
    order_user_message,
)
from app.domain.course_from_article.local_course.curriculum.collapse import (
    fit_seed_count,
    is_shell_seed,
    is_shell_title,
    merge_semantic_groups,
)
from app.domain.course_from_article.local_course.curriculum.inventory import (
    TopicSeed,
    inventory_from_sources,
)
from app.domain.course_from_article.local_course.curriculum.outline import (
    normalize_local_chapters,
    syllabus_has_excerpts,
)
from app.domain.course_from_article.local_course.curriculum.spine import build_local_book_spine
from app.domain.course_from_article.local_course.policy.policy import (
    LocalCoursePolicy,
    local_course_policy_for,
)
from app.domain.course_from_article.local_course.policy.schemas import (
    LABEL_SCHEMA,
    ORDER_SCHEMA,
    load_json_object,
)
from app.domain.course_from_article.practice.source_exercise_harvest import (
    HarvestedExercise,
    exercises_to_checkpoint,
)
from app.domain.course_from_article.workflow.events.progress import _band_progress, _stage_event
from app.domain.course_from_article.workflow.pipeline.pipeline_analyze import AnalyzeStageResult
from app.domain.course_strategies import chapter_title_is_valid, sanitize_chapter_title
from app.domain.errors import TutorError
from app.domain.llm.content.json_mode import complete_json_chat_result
from app.domain.llm.target import LlmTarget
from app.domain.ollama.runtime_policy import OllamaProfile
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest

_FOUNDATION_MARKERS = (
    "intro",
    "introduction",
    "overview",
    "what is",
    "what are",
    "basic",
    "start",
    "setup",
    "install",
    "hello",
    "начал",
    "основы ",
    "основы:",
    "установ",
    "перв",
    "введен",
    "что такое",
    "что это",
    "зачем нуж",
    "ментальн",
    "предыстор",
)

_REFERENCE_MARKERS = (
    "справочник",
    "glossary",
    "cheat sheet",
    "cheatsheet",
    "краткий справочник",
    "словарь термин",
    "шпаргал",
)
_ADVANCED_MARKERS = (
    "advanced",
    "pitfall",
    "production",
    "optim",
    "scale",
    "ловуш",
    "тонк",
    "производ",
    "best-practice",
    "best practice",
    "лучшие практик",
    "когда не",
)
_CLOSING_MARKERS = (
    "итог",
    "заключ",
    "summary",
    "conclusion",
    "wrap-up",
    "wrap up",
)


def _seed_rank(seed: TopicSeed) -> int:
    title = seed.title.casefold().strip()
    if is_shell_title(seed.title) and any(
        marker in title for marker in ("итог", "заключ", "summary", "conclusion")
    ):
        return 3
    if any(marker in title for marker in _CLOSING_MARKERS):
        return 3
    if any(marker in title for marker in _REFERENCE_MARKERS):
        return 2
    if any(marker in title for marker in _ADVANCED_MARKERS):
        return 2
    if any(marker in title for marker in _FOUNDATION_MARKERS):
        return 0
    return 1


def order_seeds_heuristic(seeds: list[TopicSeed]) -> list[TopicSeed]:
    indexed = list(enumerate(seeds))
    indexed.sort(key=lambda pair: (_seed_rank(pair[1]), pair[0]))
    return stabilize_book_order([seed for _, seed in indexed])


def stabilize_book_order(seeds: list[TopicSeed]) -> list[TopicSeed]:

    openings: list[TopicSeed] = []
    closings: list[TopicSeed] = []
    body: list[TopicSeed] = []
    for seed in seeds:
        rank = _seed_rank(seed)
        title = seed.title.casefold().strip()
        if is_shell_title(seed.title) and rank < 3:
            openings.append(seed)
        elif (
            rank >= 3
            or is_shell_title(seed.title)
            or any(marker in title for marker in ("подведение итогов", "заключение"))
        ):
            closings.append(seed)
        else:
            body.append(seed)
    return openings + body + closings


def _apply_order_ids(seeds: list[TopicSeed], order_ids: list[str]) -> list[TopicSeed] | None:
    by_id = {str(index): seed for index, seed in enumerate(seeds)}
    seen: set[str] = set()
    ordered: list[TopicSeed] = []
    for item in order_ids:
        seed = by_id.get(item)
        if seed is None or item in seen:
            continue
        ordered.append(seed)
        seen.add(item)
    if not ordered:
        return None
    for index, seed in enumerate(seeds):
        key = str(index)
        if key not in seen:
            ordered.append(seed)
    return ordered


def _compiler_payload(
    chapters: list[dict[str, str]],
    outcomes: list[str],
    *,
    ordered: bool,
    inventory: list[TopicSeed] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "chapters": chapters,
        "outcomes": outcomes,
        "ordered": ordered,
    }
    if inventory is not None:
        payload["inventory"] = [
            {
                "title": seed.title,
                "objective": seed.objective,
                "excerpt": seed.excerpt,
            }
            for seed in inventory
        ]
    return payload


async def order_seeds_with_llm(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    seeds: list[TopicSeed],
    body: CourseFromArticleRequest,
    policy: LocalCoursePolicy,
    min_topics: int = 1,
) -> tuple[list[TopicSeed], list[str]]:
    heuristic = order_seeds_heuristic(seeds)
    if len(seeds) < 2:
        return heuristic, []
    last_outcomes: list[str] = []
    for _ in range(policy.outline_retries + 1):
        try:
            result = await complete_json_chat_result(
                client,
                target,
                system_prompt=order_system_prompt(),
                user_message=order_user_message(seeds, locale=body.locale or "ru"),
                temperature=policy.schema_temperature,
                max_tokens=COURSE_LLM.order_max_tokens,
                num_ctx=target.num_ctx,
                json_schema=ORDER_SCHEMA,
            )
            payload = await load_json_object(
                client,
                target,
                result.content,
                hint="syllabus order: JSON object with order and outcomes",
                max_tokens=COURSE_LLM.order_max_tokens,
                num_ctx=target.num_ctx,
            )
        except (TutorError, httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError):
            continue
        raw_order = payload.get("order")
        if not isinstance(raw_order, list):
            continue
        order_ids = [str(item).strip() for item in raw_order if str(item).strip()]
        ordered = _apply_order_ids(seeds, order_ids)
        raw_outcomes = payload.get("outcomes")
        if isinstance(raw_outcomes, list):
            last_outcomes = [str(item).strip() for item in raw_outcomes if str(item).strip()][:6]
        if ordered:
            raw_groups = payload.get("merge_groups")
            groups = (
                [
                    [str(item).strip() for item in group if str(item).strip()]
                    for group in raw_groups
                    if isinstance(group, list)
                ]
                if isinstance(raw_groups, list)
                else []
            )
            synthesized = merge_semantic_groups(seeds, ordered, groups, min_topics=min_topics)
            return stabilize_book_order(synthesized), last_outcomes
    return stabilize_book_order(heuristic), last_outcomes


def _seeds_from_chapters(chapters: list[dict[str, str]]) -> list[TopicSeed]:
    return [
        TopicSeed(
            title=item["title"],
            objective=item.get("objective") or item["title"],
            excerpt=item.get("source_excerpt") or "",
            source_title="",
            order=index,
        )
        for index, item in enumerate(chapters)
    ]


def seeds_to_chapters(
    seeds: list[TopicSeed],
    *,
    max_chapters: int,
    locale: str = "ru",
) -> list[dict[str, str]]:
    raw = [
        {
            "id": f"t{index + 1}",
            "title": seed.title,
            "objective": seed.objective,
            "source_excerpt": seed.excerpt,
        }
        for index, seed in enumerate(seed for seed in seeds if not is_shell_seed(seed))
    ]
    return normalize_local_chapters(raw, max_chapters=max_chapters, locale=locale)


def _relabel_from_payload(
    chapters: list[dict[str, str]],
    outcomes: list[str],
    payload: dict[str, object],
) -> tuple[list[dict[str, str]], list[str]] | None:
    raw = payload.get("chapters")
    if not isinstance(raw, list):
        return None
    by_id = {str(item.get("id") or ""): item for item in raw if isinstance(item, dict)}
    relabeled: list[dict[str, str]] = []
    for chapter in chapters:
        patch = by_id.get(chapter["id"])
        if not isinstance(patch, dict):
            relabeled.append(chapter)
            continue
        candidate = sanitize_chapter_title(
            str(patch.get("title") or ""),
            fallback=chapter["title"],
        )

        if chapter_title_is_valid(candidate) and not is_shell_title(candidate):
            title = candidate
        else:
            title = chapter["title"]
        objective = (
            str(patch.get("objective") or chapter.get("objective") or title).strip() or title
        )
        relabeled.append({**chapter, "title": title[:160], "objective": objective[:400]})
    raw_outcomes = payload.get("outcomes")
    new_outcomes = (
        [str(item).strip() for item in raw_outcomes if str(item).strip()][:6]
        if isinstance(raw_outcomes, list)
        else []
    )
    return relabeled, new_outcomes or outcomes


async def localize_chapter_labels(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    policy: LocalCoursePolicy,
) -> tuple[list[dict[str, str]], list[str]]:
    if not chapters:
        return chapters, outcomes
    locale = normalize_course_locale(body.locale)
    if not catalog_needs_locale_rewrite(chapters, outcomes, locale):
        return chapters, outcomes
    snapshot = [
        {"id": item["id"], "title": item["title"], "objective": item.get("objective") or ""}
        for item in chapters
    ]
    last: tuple[list[dict[str, str]], list[str]] | None = None
    for _ in range(policy.outline_retries + 1):
        try:
            result = await complete_json_chat_result(
                client,
                target,
                system_prompt=(
                    f"{locale_line(locale)} "
                    "Source headings may be in the article language — that does not matter. "
                    "Rewrite every title, objective, and outcome into the course locale. "
                    "Keep API and library names. Same ids. Do not invent chapters."
                ),
                user_message=(
                    f"{locale_line(locale)}\n"
                    "Return JSON chapters with the same ids, already translated.\n"
                    f"Chapters:\n{json.dumps(snapshot, ensure_ascii=False)}\n"
                    f"Outcomes:\n{json.dumps(outcomes, ensure_ascii=False)}"
                ),
                temperature=policy.schema_temperature,
                max_tokens=COURSE_LLM.outline_label_max_tokens,
                num_ctx=target.num_ctx,
                json_schema=LABEL_SCHEMA,
            )
            payload = await load_json_object(
                client,
                target,
                result.content,
                hint="chapter labels: JSON object with translated chapters",
                max_tokens=COURSE_LLM.outline_label_max_tokens,
                num_ctx=target.num_ctx,
            )
        except (TutorError, httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError):
            continue
        applied = _relabel_from_payload(chapters, outcomes, payload)
        if applied is None:
            continue
        last = applied
        if not catalog_needs_locale_rewrite(applied[0], applied[1], locale):
            return applied
    return last or (chapters, outcomes)


def apply_syllabus_to_outline(
    outline: AnalyzeStageResult,
    *,
    body: CourseFromArticleRequest,
    article: str,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    source_title: str = "",
) -> None:
    outline.chapters = chapters
    outline.outcomes = outcomes or [item["objective"] for item in chapters[:6]]
    locale = normalize_course_locale(body.locale)
    title = (body.title or "").strip()
    if catalog_text_mismatches_locale(title, locale):
        title = ""
    grounded_title = " ".join(source_title.split()).strip()
    if catalog_text_mismatches_locale(grounded_title, locale):
        grounded_title = ""
    if grounded_title.casefold() in {"item", "article", "topic", "source"}:
        grounded_title = ""
    title = title or grounded_title or (chapters[0]["title"] if chapters else "Article Course")
    outline.title = title
    outline.pack_id = _slug(title)
    outline.domain = _normalize_domain(None, article=article, title=title)
    outline.book_spine = build_local_book_spine(
        locale=locale,
        title=title,
        chapters=chapters,
        outcomes=list(outline.outcomes),
    )
    outline.locale = locale
    outline.warning = None


def course_title_from_sources(
    sources: list[dict[str, object]],
    *,
    locale: str,
) -> str:
    for source in sources:
        title = " ".join(str(source.get("title") or "").split()).strip()
        if (
            title
            and title.casefold() not in {"item", "article", "topic", "source"}
            and not catalog_text_mismatches_locale(title, normalize_course_locale(locale))
        ):
            return title[:160]
    return ""


def _saved_compiler_state(
    saved: object,
    *,
    cap: int,
    locale: str,
) -> tuple[list[dict[str, str]], list[str], bool] | None:
    if not isinstance(saved, dict):
        return None
    chapters = normalize_local_chapters(
        saved.get("chapters"),
        max_chapters=cap,
        locale=locale,
    )
    raw_outcomes = saved.get("outcomes")
    outcomes = (
        [str(item).strip() for item in raw_outcomes if str(item).strip()]
        if isinstance(raw_outcomes, list)
        else []
    )
    if not chapters or not syllabus_has_excerpts(chapters):
        return None
    return chapters, outcomes, saved.get("ordered", True) is not False


async def _restore_compiled_syllabus(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    policy: LocalCoursePolicy,
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    cap: int,
    floor: int,
) -> tuple[list[dict[str, str]], list[str]] | None:
    restored = _saved_compiler_state(
        store.load_compiler(user_id, build_id),
        cap=cap,
        locale=str(body.locale or "ru"),
    )
    if restored is None:
        return None
    chapters, outcomes, is_ordered = restored
    inventory = None if is_ordered else _seeds_from_chapters(chapters)
    if inventory is not None:
        ordered, llm_outcomes = await order_seeds_with_llm(
            client,
            target,
            seeds=inventory,
            body=body,
            policy=policy,
            min_topics=floor,
        )
        chapters = seeds_to_chapters(
            ordered,
            max_chapters=cap,
            locale=str(body.locale or "ru"),
        )
        outcomes = llm_outcomes or outcomes
    labeled, labeled_outcomes = await localize_chapter_labels(
        client,
        target,
        body=body,
        chapters=chapters,
        outcomes=outcomes,
        policy=policy,
    )
    if inventory is not None or labeled != chapters or labeled_outcomes != outcomes:
        store.save_compiler(
            user_id,
            build_id,
            _compiler_payload(
                labeled,
                labeled_outcomes,
                ordered=True,
                inventory=inventory,
            ),
        )
    return labeled, labeled_outcomes


async def _compile_source_inventory(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    sources: list[dict[str, object]],
    article: str,
    policy: LocalCoursePolicy,
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    cap: int,
    floor: int,
) -> tuple[list[dict[str, str]], list[str]] | None:
    seeds = inventory_from_sources(
        sources,
        article=article,
        sentences_per_window=policy.sentences_per_window,
    )
    fitted = fit_seed_count(seeds, max_chapters=cap, min_topics=floor)
    if not fitted:
        return None
    store.save_compiler(
        user_id,
        build_id,
        _compiler_payload(
            seeds_to_chapters(
                fitted,
                max_chapters=cap,
                locale=str(body.locale or "ru"),
            ),
            [],
            ordered=False,
            inventory=fitted,
        ),
    )
    ordered, outcomes = await order_seeds_with_llm(
        client,
        target,
        seeds=fitted,
        body=body,
        policy=policy,
        min_topics=floor,
    )
    chapters = seeds_to_chapters(
        ordered,
        max_chapters=cap,
        locale=str(body.locale or "ru"),
    )
    labeled, labeled_outcomes = await localize_chapter_labels(
        client,
        target,
        body=body,
        chapters=chapters,
        outcomes=outcomes,
        policy=policy,
    )
    store.save_compiler(
        user_id,
        build_id,
        _compiler_payload(labeled, labeled_outcomes, ordered=True, inventory=fitted),
    )
    return labeled, labeled_outcomes


async def compile_local_syllabus(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    sources: list[dict[str, object]],
    article: str,
    policy: LocalCoursePolicy,
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    warnings: list[str],
) -> tuple[list[dict[str, str]], list[str]]:

    corpus_chars = corpus_char_count(sources, article)
    cap = chapter_ceiling(body, corpus_chars=corpus_chars, hard_max=policy.max_chapters)
    floor = chapter_floor(body, corpus_chars=corpus_chars, ceiling=cap)
    wanted = min(body.effective_theory_count() or cap, cap)
    restored = await _restore_compiled_syllabus(
        client,
        target,
        body=body,
        policy=policy,
        store=store,
        user_id=user_id,
        build_id=build_id,
        cap=cap,
        floor=floor,
    )
    if restored is not None:
        return restored
    compiled = await _compile_source_inventory(
        client,
        target,
        body=body,
        sources=sources,
        article=article,
        policy=policy,
        store=store,
        user_id=user_id,
        build_id=build_id,
        cap=cap,
        floor=floor,
    )
    if compiled is None:
        warnings.append("local compiler: empty inventory")
        return [], []
    labeled, labeled_outcomes = compiled
    if wanted and len(labeled) < wanted:
        warnings.append(
            f"local compiler: {len(labeled)} unique topics from sources (requested {wanted})"
        )
    return labeled, labeled_outcomes


async def iter_local_outline_stage(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    article: str,
    sources: list[dict[str, object]],
    band_analyze: tuple[float, float],
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    build_meta: CourseBuildMeta,
    exercise_seeds: list[HarvestedExercise],
    warnings: list[str],
    outline: AnalyzeStageResult,
    ollama_profile: OllamaProfile,
) -> AsyncIterator[dict[str, object]]:
    policy = local_course_policy_for(profile=ollama_profile, model=target.model)
    yield _stage_event(
        stage="analyze",
        status="running",
        progress=_band_progress(band_analyze, 0, 1),
        message="Compiling syllabus from sources",
        message_key="analyzeCompiling",
        detail={"build_id": str(build_id), "phase": "compile"},
    )
    chapters, outcomes = await compile_local_syllabus(
        client,
        target,
        body=body,
        sources=sources,
        article=article,
        policy=policy,
        store=store,
        user_id=user_id,
        build_id=build_id,
        warnings=warnings,
    )
    if not chapters:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course analyze returned no chapters")
    apply_syllabus_to_outline(
        outline,
        body=body,
        article=article,
        chapters=chapters,
        outcomes=outcomes,
        source_title=course_title_from_sources(sources, locale=str(body.locale or "ru")),
    )
    store.save_analyze(
        user_id,
        build_id,
        {
            "chapters": outline.chapters,
            "book_spine": outline.book_spine,
            "outcomes": outline.outcomes,
            "domain": outline.domain,
            "course_profile": outline.course_profile,
            "pack_id": outline.pack_id,
            "title": outline.title,
            "locale": outline.locale,
            "exercise_seeds": exercises_to_checkpoint(exercise_seeds),
        },
    )
    store.patch_meta(
        user_id,
        build_id,
        title=outline.title or build_meta.title,
        stage="analyze",
        chapter_total=len(outline.chapters),
        clear_error=True,
    )
    skeleton = [{"id": item["id"], "title": item["title"]} for item in chapters]
    yield _stage_event(
        stage="analyze",
        status="done",
        progress=band_analyze[1],
        message="Syllabus compiled from sources",
        message_key="analyzeOutlineReady",
        detail={
            "title": outline.title,
            "pack_id": outline.pack_id,
            "domain": outline.domain,
            "outcomes": outline.outcomes,
            "chapters": skeleton,
            "chapter_count": len(chapters),
            "phase": "compile",
        },
    )
