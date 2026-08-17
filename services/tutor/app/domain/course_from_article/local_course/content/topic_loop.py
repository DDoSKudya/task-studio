from __future__ import annotations

import json
import logging
import re
import uuid
from collections.abc import Callable
from functools import partial
from typing import NoReturn

import httpx
from app.domain.course_build import CourseBuildStore
from app.domain.course_from_article.local_course.content.fallbacks import (
    practice_from_chapter_theory,
    quizzes_from_chapter_theory,
)
from app.domain.course_from_article.local_course.content.messages import (
    practice_patch_user_message,
    practice_system_prompt,
    practice_user_message,
    quiz_patch_user_message,
    quiz_system_prompt,
    quiz_user_message,
)
from app.domain.course_from_article.local_course.content.theory import expand_local_theory_chapter
from app.domain.course_from_article.local_course.policy.heuristics import (
    normalize_practice_task,
    practice_must_fix,
    practice_spec_is_usable,
    quiz_item_is_usable,
    quiz_must_fix,
    starter_from_brief,
)
from app.domain.course_from_article.local_course.policy.policy import LocalCoursePolicy
from app.domain.course_from_article.local_course.policy.schemas import (
    PRACTICE_ITEM_SCHEMA,
    QUIZ_ITEM_SCHEMA,
    load_json_object,
    payload_items,
)
from app.domain.course_from_article.practice.source_exercise_harvest import HarvestedExercise
from app.domain.course_strategies import (
    choices_are_letter_only,
    detect_practice_runtime,
    practice_template_looks_fake,
    question_embeds_choices,
    quiz_stem_key,
    quiz_stems_overlap,
    strip_inline_choice_letters,
)
from app.domain.errors import TutorError
from app.domain.llm.content.json_mode import complete_json_chat_result
from app.domain.llm.target import LlmTarget
from fastapi import status
from studio_contracts.api.studio_schemas import CourseFromArticleRequest

logger = logging.getLogger(__name__)

_SOFT_LLM = (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError)

_STEM_REPEAT_OVERLAP = 0.5


def _body_locale(body: CourseFromArticleRequest) -> str:
    return str(body.locale or "ru")


def _fail_local_assess(kind: str, chapter: dict[str, str], reason: str) -> NoReturn:
    title = str(chapter.get("title") or chapter.get("id") or "chapter")
    raise TutorError(
        status.HTTP_502_BAD_GATEWAY,
        f"local {kind} failed for «{title}»: {reason}",
    )


def _article_seed_block(
    seeds: list[HarvestedExercise] | None,
    *,
    kinds: tuple[str, ...],
) -> str:
    if not seeds:
        return ""
    blocks = [item.as_prompt_block() for item in seeds if item.kind in kinds][:4]
    return "\n\n".join(blocks)


def _slug_id(prefix: str, index: int) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", prefix.casefold()).strip("-")
    return f"{cleaned or 'topic'}-{index}"[:96]


def _chapter_with_source(chapter: dict[str, str], article: str) -> dict[str, str]:
    _ = article
    return chapter


async def generate_topic_theory(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    policy: LocalCoursePolicy,
    prior_chapter_digest: str = "",
    article: str = "",
    book_spine: dict[str, str] | None = None,
    next_title: str = "",
    store: CourseBuildStore | None = None,
    user_id: uuid.UUID | None = None,
    build_id: uuid.UUID | None = None,
) -> dict[str, object]:
    sourced = _chapter_with_source(chapter, article)
    return await expand_local_theory_chapter(
        client,
        target,
        body=body,
        chapter=sourced,
        policy=policy,
        prior_chapter_digest=prior_chapter_digest,
        book_spine=book_spine,
        next_title=next_title,
        store=store,
        user_id=user_id,
        build_id=build_id,
    )


def _folded_get(item: dict[str, object], *names: str) -> object:
    folded = {str(key).casefold(): value for key, value in item.items()}
    for name in names:
        if name.casefold() in folded:
            return folded[name.casefold()]
    return None


_CHOICE_LABEL_RE = re.compile(r"^[A-Da-d1-4][).\:]\s*")


def _choice_texts(choices: object) -> list[str]:
    if isinstance(choices, dict):
        ordered_keys = ("a", "b", "c", "d", "1", "2", "3", "4", "0")
        texts: list[str] = []
        seen: set[str] = set()
        for key in ordered_keys:
            for raw_key, raw_value in choices.items():
                if str(raw_key).casefold() != key:
                    continue
                text = _clean_choice_text(raw_value)
                if text and text.casefold() not in seen:
                    seen.add(text.casefold())
                    texts.append(text)
        for raw_value in choices.values():
            text = _clean_choice_text(raw_value)
            if text and text.casefold() not in seen:
                seen.add(text.casefold())
                texts.append(text)
        return texts[:4]
    if not isinstance(choices, list):
        return []
    listed: list[str] = []
    for item in choices:
        if isinstance(item, str):
            text = _clean_choice_text(item)
        elif isinstance(item, dict):
            text = _clean_choice_text(_folded_get(item, "text", "label", "value", "choice") or "")
        else:
            text = _clean_choice_text(item)
        if text:
            listed.append(text)
    return listed


def _clean_choice_text(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return _CHOICE_LABEL_RE.sub("", text).strip()[:200]


def _complete_choice_set(
    choices: list[str],
    *,
    question: str,
    answer: object,
) -> list[str]:
    if len(choices) != 3:
        return choices
    answer_index = _answer_index(answer, choices=choices)
    if not 0 <= answer_index < len(choices):
        return choices
    correct = choices[answer_index].rstrip(".")
    if re.search(r"[А-Яа-яЁё]", f"{question} {correct}"):
        distractor = f"Неверно, что {correct}"
    else:
        distractor = f"It is false that {correct}"
    if distractor.casefold() in {choice.casefold() for choice in choices}:
        return choices
    return [*choices, distractor[:200]]


def _answer_index(value: object, *, choices: list[str] | None = None) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("+-").isdigit():
            return int(stripped)
        letter = stripped[:1].casefold()
        if letter in "abcd":
            return "abcd".index(letter)
        if choices:
            folded = stripped.casefold()
            for index, choice in enumerate(choices):
                if choice.casefold() == folded:
                    return index
    return 0


_INLINE_CHOICE_RE = re.compile(r"(?m)^\s*(?:[-*]\s*)?(?:([A-Da-d])|[1-4])[).\:]\s*(\S.*)$")


def _choices_from_question_text(question: str) -> tuple[str, list[str]]:

    lines = (question or "").splitlines()
    stem_lines: list[str] = []
    choices: list[str] = []
    for line in lines:
        match = _INLINE_CHOICE_RE.match(line.strip())
        if match is None:
            if choices:
                continue
            stem_lines.append(line)
            continue
        text = match.group(2).strip()[:200]
        if text and text.casefold() not in {item.casefold() for item in choices}:
            choices.append(text)
    stem = "\n".join(stem_lines).strip() or (question or "").strip()

    if len(choices) < 4:
        inline = re.findall(
            r"(?:^|[\s;])([A-Da-d]|[1-4])[).\:]\s*([^A-D1-4]+?)(?=(?:\s+[A-D1-4][).\:])|$)",
            question or "",
            flags=re.IGNORECASE,
        )
        if len(inline) >= 4:
            choices = [text.strip()[:200] for _, text in inline[:4] if text.strip()]
            cut = re.search(r"(?:^|[\s;])([A-Da-d]|[1-4])[).\:]", question or "")
            if cut is not None:
                stem = (question or "")[: cut.start()].strip(" ?\n\t;") + "?"
    return stem.strip(), choices[:4]


def _quiz_title(question: str, index: int, explicit: object) -> str:
    titled = str(explicit or "").strip()
    if titled and not titled.casefold().startswith("check "):
        return titled[:120]
    stem = re.sub(r"\s+", " ", (question or "").strip())
    if len(stem) >= 12:
        return _title_from_stem(stem, index)
    return f"Check {index}"[:120]


def _title_from_stem(stem: str, index: int) -> str:

    first = re.split(r"(?<=[.!?])\s+", stem)[0].strip(" .!?")
    if len(first) <= 64:
        return first[:120] or f"Check {index}"
    words = first.split()
    short = " ".join(words[:8]).strip(" ,;:—-")
    return (short or first[:64]).rstrip(" ,;:—-")[:120]


def _stem_without_choices(question: str, choices: list[str]) -> str:

    if not question_embeds_choices(question, choices):
        return question
    stem, _ = strip_inline_choice_letters(question)
    if len(stem) >= 12 and not question_embeds_choices(stem, choices):
        return stem
    cuts = [
        question.find(choice)
        for choice in choices
        if len(choice) > 15 and question.find(choice) > 12
    ]
    if not cuts:
        return question
    trimmed = question[: min(cuts)].rstrip()
    trimmed = re.sub(r"[\s\n]*[A-Da-dА-Га-г][).:]\s*$", "", trimmed).rstrip()
    return trimmed if len(trimmed) >= 12 else question


def _quiz_from_item(
    item: dict[str, object],
    *,
    topic_key: str,
    index: int,
) -> dict[str, object] | None:
    nested = _folded_get(item, "quiz", "item")
    if isinstance(nested, dict):
        item = {**item, **nested}
    question = str(_folded_get(item, "question", "stem", "prompt", "q", "text") or "").strip()
    choices = _choice_texts(
        _folded_get(item, "choices", "options", "answers", "variants", "answers_list")
    )
    if len(choices) < 4 and question:
        stem, inline = _choices_from_question_text(question)
        if len(inline) >= 4:
            question = stem
            choices = inline
    answer = _folded_get(item, "answer", "correct", "correct_index")
    choices = _complete_choice_set(choices, question=question, answer=answer)
    if choices_are_letter_only(choices):
        repaired_stem, repaired = strip_inline_choice_letters(question)
        if repaired and len(repaired) >= 4 and not choices_are_letter_only(repaired):
            question = repaired_stem
            choices = repaired[:4]
        else:
            return None
    if len(choices) < 4:
        return None
    question = _stem_without_choices(question, choices)
    if len(question) < 12:
        return None
    if len(question) < 25 and max(len(str(item)) for item in choices) < 12:
        return None
    return {
        "id": _slug_id(f"{topic_key}-quiz", index),
        "kind": "quiz",
        "title": _quiz_title(question, index, _folded_get(item, "title")),
        "question": question[:400],
        "choices": choices[:4],
        "answer": max(
            0,
            min(
                3,
                _answer_index(
                    answer,
                    choices=choices,
                ),
            ),
        ),
    }


def _coerce_folded_text(value: object) -> str:

    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list | tuple):
        parts = [_coerce_folded_text(item) for item in value]
        return "\n".join(part for part in parts if part).strip()
    if isinstance(value, dict):
        for key in (
            "template",
            "starter",
            "starter_code",
            "code",
            "content",
            "text",
            "brief",
            "java",
            "python",
            "go",
            "javascript",
            "typescript",
            "start",
            "body",
        ):
            if key in value:
                text = _coerce_folded_text(value.get(key))
                if text:
                    return text
        return ""
    if isinstance(value, int | float | bool):
        return str(value).strip()
    return ""


def _folded_text(item: dict[str, object], *names: str) -> str:
    for name in names:
        value = _folded_get(item, name)
        text = _coerce_folded_text(value)
        if text:
            return text
    return ""


def _practice_from_item(
    item: dict[str, object],
    *,
    topic_key: str,
    index: int,
    theory: str = "",
    fallback_runtime: str = "",
) -> dict[str, object] | None:
    nested = _folded_get(item, "task", "item", "practice")
    if isinstance(nested, dict):
        item = {**item, **nested}
    title = _folded_text(item, "title", "name", "heading", "label", "chapter")
    content = _folded_text(
        item,
        "content",
        "brief",
        "prompt",
        "description",
        "instruction",
        "task",
        "text",
    )
    template = _folded_text(
        item,
        "template",
        "starter",
        "starter_code",
        "code",
        "skeleton",
        "scaffold",
    )
    if not template:
        template = starter_from_brief(content) or starter_from_brief(theory)
    if not content and title:
        content = title
    if not title and content:
        title = _title_from_stem(re.sub(r"\s+", " ", content).strip(), index)

    if title and len(title) < 8 and content:
        title = re.sub(r"\s+", " ", f"{title}: {content}").strip()[:120]
    if not title or not content:
        return None
    runtime = (
        fallback_runtime or detect_practice_runtime(f"{theory}\n{content}\n{template}") or "python"
    )
    if practice_template_looks_fake(template, source_text=f"{theory}\n{content}"):
        template = ""
    return normalize_practice_task(
        {
            "id": _slug_id(f"{topic_key}-code", index),
            "kind": "code",
            "title": title[:120],
            "content": content[:2000],
            "template": template[:4000],
            "tests": [],
            "checker": "llm",
            "rubric": content[:240],
            "level": (_folded_text(item, "level") or "medium")[:24],
            "runtime": runtime,
        },
        theory=theory,
    )


async def _ensure_quiz_usable(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    quiz: dict[str, object],
    theory: str,
    policy: LocalCoursePolicy,
    topic_key: str,
    index: int,
) -> dict[str, object] | None:
    locale = _body_locale(body)
    if quiz_item_is_usable(quiz, theory=theory, locale=locale):
        return quiz
    fixes = quiz_must_fix(quiz, theory=theory, locale=locale)
    logger.warning(
        "quiz rejected [%s #%d]: %s | q=%r",
        topic_key,
        index,
        "; ".join(fixes) or "unknown",
        str(quiz.get("question") or "")[:120],
    )
    if policy.quality_rounds < 1:
        return None
    try:
        result = await complete_json_chat_result(
            client,
            target,
            system_prompt=quiz_system_prompt(locale, chunk=1),
            user_message=quiz_patch_user_message(
                locale=locale,
                theory=theory,
                quiz=quiz,
                must_fix=fixes,
            ),
            temperature=policy.schema_temperature,
            max_tokens=policy.quiz_max_tokens,
            num_ctx=target.num_ctx,
            json_schema=QUIZ_ITEM_SCHEMA,
        )
        payload = await load_json_object(
            client,
            target,
            result.content,
            hint="quiz patch: one JSON object with quizzes",
            max_tokens=policy.quiz_max_tokens,
            num_ctx=target.num_ctx,
        )
        raw_items = payload_items(payload, plural="quizzes", singular="quiz")
        if not raw_items and payload.get("question"):
            raw_items = [payload]
        if not raw_items:
            logger.warning("quiz patch returned empty items [%s #%d]", topic_key, index)
            return None
        first = raw_items[0]
        if not isinstance(first, dict):
            logger.warning("quiz patch first item not a dict [%s #%d]: %r", topic_key, index, first)
            return None
        patched = _quiz_from_item(first, topic_key=topic_key, index=index)
        if patched is None:
            logger.warning(
                "quiz patch item invalid (missing q/choices) [%s #%d]: choices=%r q=%r",
                topic_key,
                index,
                first.get("choices"),
                str(first.get("question") or "")[:80],
            )
    except _SOFT_LLM as exc:
        logger.warning(
            "quiz patch JSON unreadable [%s #%d]: %s: %s",
            topic_key,
            index,
            type(exc).__name__,
            exc,
        )
        return None
    if patched is not None:
        if quiz_item_is_usable(patched, theory=theory, locale=locale):
            return patched
        remaining = quiz_must_fix(patched, theory=theory, locale=locale)
        logger.warning(
            "quiz patch still rejected [%s #%d]: %s | q=%r",
            topic_key,
            index,
            "; ".join(remaining) or "unknown",
            str(patched.get("question") or "")[:120],
        )
    return None


async def _ensure_practice_usable(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    task: dict[str, object],
    theory: str,
    policy: LocalCoursePolicy,
    topic_key: str,
    index: int,
) -> dict[str, object] | None:
    locale = _body_locale(body)
    current = normalize_practice_task(task, theory=theory)
    if practice_spec_is_usable(current, locale=locale, theory=theory):
        return current
    rounds = max(0, policy.quality_rounds)
    if rounds < 1:
        return None
    for _ in range(rounds):
        try:
            result = await complete_json_chat_result(
                client,
                target,
                system_prompt=practice_system_prompt(locale),
                user_message=practice_patch_user_message(
                    locale=locale,
                    theory=theory,
                    task=current,
                    must_fix=practice_must_fix(current, locale=locale, theory=theory),
                ),
                temperature=policy.schema_temperature,
                max_tokens=policy.practice_max_tokens,
                num_ctx=target.num_ctx,
                json_schema=PRACTICE_ITEM_SCHEMA,
            )
            payload = await load_json_object(
                client,
                target,
                result.content,
                hint="practice patch: one JSON object with tasks",
                max_tokens=policy.practice_max_tokens,
                num_ctx=target.num_ctx,
            )
            raw_items = payload_items(payload, plural="tasks", singular="task")
            if not raw_items and (payload.get("title") or payload.get("template")):
                raw_items = [payload]
            if not raw_items:
                continue
            first = raw_items[0]
            if not isinstance(first, dict):
                continue
            patched = _practice_from_item(
                first,
                topic_key=topic_key,
                index=index,
                theory=theory,
            )
        except _SOFT_LLM as exc:
            logger.warning(
                "practice patch JSON unreadable [%s #%d]: %s: %s",
                topic_key,
                index,
                type(exc).__name__,
                exc,
            )
            continue
        if patched is None:
            continue
        patched = normalize_practice_task(patched, theory=theory)
        if practice_spec_is_usable(patched, locale=locale, theory=theory):
            return patched
        current = patched
    return None


async def _quiz_chunk(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    theory: dict[str, object],
    policy: LocalCoursePolicy,
    topic_key: str,
    chunk: int,
    start_index: int,
    already_questions: list[str],
    article_seeds: str = "",
    prior_digest: str = "",
    chapter_index: int = 0,
    chapter_total: int = 1,
    novelty_nudge: str = "",
) -> list[dict[str, object]]:
    theory_blob = str(theory.get("content") or "")
    locale = _body_locale(body)
    system = quiz_system_prompt(locale, chunk=chunk)
    user = quiz_user_message(
        locale=locale,
        chunk=chunk,
        title=chapter["title"],
        objective=chapter.get("objective") or "",
        theory=theory_blob,
        already=already_questions,
        article_seeds=article_seeds,
        prior_digest=prior_digest,
        chapter_index=chapter_index,
        chapter_total=chapter_total,
    )
    if novelty_nudge.strip():
        user = f"{user}\n{novelty_nudge.strip()}\n"
    for attempt in range(min(2, policy.topic_retries + 1)):
        try:
            result = await complete_json_chat_result(
                client,
                target,
                system_prompt=system,
                user_message=user
                + (f"\nRetry {attempt}: previous JSON was unusable." if attempt else ""),
                temperature=policy.schema_temperature,
                max_tokens=policy.quiz_max_tokens,
                num_ctx=target.num_ctx,
                json_schema=QUIZ_ITEM_SCHEMA if chunk == 1 else None,
            )
            payload = await load_json_object(
                client,
                target,
                result.content,
                hint="quiz JSON: question + 4 choices + answer",
                max_tokens=policy.quiz_max_tokens,
                num_ctx=target.num_ctx,
            )
            raw_items = payload_items(payload, plural="quizzes", singular="quiz")
            if not raw_items:
                logger.warning(
                    "quiz payload empty [%s] attempt=%s keys=%s",
                    topic_key,
                    attempt,
                    list(payload.keys()),
                )
                continue
            parsed: list[dict[str, object]] = []
            for offset, item in enumerate(raw_items[:chunk]):
                if not isinstance(item, dict):
                    logger.warning("quiz item not a dict [%s]: %r", topic_key, item)
                    continue
                quiz = _quiz_from_item(item, topic_key=topic_key, index=start_index + offset)
                if quiz is None:
                    logger.warning(
                        "quiz item invalid [%s]: keys=%s choices=%r q=%r",
                        topic_key,
                        list(item.keys()),
                        item.get("choices") or item.get("options"),
                        str(item.get("question") or item.get("stem") or item.get("q") or "")[:80],
                    )
                    continue
                usable = await _ensure_quiz_usable(
                    client,
                    target,
                    body=body,
                    quiz=quiz,
                    theory=theory_blob,
                    policy=policy,
                    topic_key=topic_key,
                    index=start_index + offset,
                )
                if usable is not None:
                    parsed.append(usable)
            if parsed:
                return parsed[:chunk]
        except _SOFT_LLM as exc:
            logger.warning(
                "quiz JSON unreadable [%s] attempt=%s: %s: %s",
                topic_key,
                attempt,
                type(exc).__name__,
                exc,
            )
            continue
    return []


async def _practice_chunk(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    theory: dict[str, object],
    policy: LocalCoursePolicy,
    topic_key: str,
    chunk: int,
    start_index: int,
    already_titles: list[str],
    article_seeds: str = "",
    runtime: str = "",
) -> list[dict[str, object]]:
    locale = _body_locale(body)
    theory_blob = str(theory.get("content") or "")
    effective_runtime = runtime or str(body.runtime or "python")
    system = practice_system_prompt(locale)
    user = practice_user_message(
        locale=locale,
        runtime=effective_runtime,
        runtime_version=str(body.runtime_version or ""),
        chunk=chunk,
        title=chapter["title"],
        objective=chapter.get("objective") or "",
        theory=theory_blob,
        already=already_titles,
        article_seeds=article_seeds,
    )
    last_reason = "no usable tasks after retries"
    for attempt in range(min(2, policy.topic_retries + 1)):
        try:
            result = await complete_json_chat_result(
                client,
                target,
                system_prompt=system,
                user_message=user
                + (f"\nRetry {attempt}: previous JSON was unusable." if attempt else ""),
                temperature=policy.schema_temperature,
                max_tokens=policy.practice_max_tokens,
                num_ctx=target.num_ctx,
                json_schema=PRACTICE_ITEM_SCHEMA if chunk == 1 else None,
            )
            payload = await load_json_object(
                client,
                target,
                result.content,
                hint="practice batch: JSON object with tasks",
                max_tokens=policy.practice_max_tokens,
                num_ctx=target.num_ctx,
            )
            raw_items = payload_items(payload, plural="tasks", singular="task")
            if not raw_items and (
                payload.get("title")
                or payload.get("brief")
                or payload.get("content")
                or payload.get("template")
                or payload.get("prompt")
            ):
                raw_items = [payload]
            if not raw_items:
                last_reason = "JSON without tasks"
                continue
            parsed: list[dict[str, object]] = []
            for offset, item in enumerate(raw_items[:chunk]):
                if not isinstance(item, dict):
                    continue
                task = _practice_from_item(
                    item,
                    topic_key=topic_key,
                    index=start_index + offset,
                    theory=theory_blob,
                    fallback_runtime=effective_runtime,
                )
                if task is None:
                    last_reason = f"missing title or brief (keys={list(item.keys())})"
                    continue
                usable = await _ensure_practice_usable(
                    client,
                    target,
                    body=body,
                    task=task,
                    theory=theory_blob,
                    policy=policy,
                    topic_key=topic_key,
                    index=start_index + offset,
                )
                if usable is not None:
                    parsed.append(usable)
                    continue
                fixes = practice_must_fix(task, locale=locale, theory=theory_blob)
                last_reason = "; ".join(fixes) if fixes else "quality gate rejected the task"
            if parsed:
                return parsed[:chunk]
        except _SOFT_LLM as exc:
            last_reason = f"{type(exc).__name__}: {exc}"
            continue
    logger.warning(
        "local practice unusable for «%s»: %s",
        chapter.get("title"),
        last_reason,
    )
    return []


async def generate_topic_quizzes(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    theory: dict[str, object],
    count: int,
    policy: LocalCoursePolicy,
    topic_key: str,
    warnings: list[str],
    already: list[dict[str, object]] | None = None,
    persist: Callable[[list[dict[str, object]]], None] | None = None,
    exercise_seeds: list[HarvestedExercise] | None = None,
    prior_digest: str = "",
    course_already_questions: list[str] | None = None,
    chapter_index: int = 0,
    chapter_total: int = 1,
) -> list[dict[str, object]]:
    if count <= 0 or not getattr(body, "include_quizzes", True):
        return []
    theory_blob = str(theory.get("content") or "")
    article_seeds = _article_seed_block(exercise_seeds, kinds=("quiz", "open"))
    locale = _body_locale(body)
    course_seen = [
        item.strip()
        for item in (course_already_questions or [])
        if isinstance(item, str) and item.strip()
    ]
    quizzes = [
        item
        for item in (already or [])
        if quiz_item_is_usable(item, theory=theory_blob, locale=locale)
    ][:count]
    batch = max(1, policy.quiz_batch_size)
    while len(quizzes) < count:
        chunk = min(batch, count - len(quizzes))
        prompt_questions, all_seen_questions = _quiz_question_history(course_seen, quizzes)
        extra, duplicate_only = await _new_quiz_chunk(
            client,
            target,
            body=body,
            chapter=chapter,
            theory=theory,
            policy=policy,
            topic_key=topic_key,
            chunk=chunk,
            start_index=len(quizzes) + 1,
            prompt_questions=prompt_questions,
            all_seen_questions=all_seen_questions,
            article_seeds=article_seeds,
            prior_digest=prior_digest,
            chapter_index=chapter_index,
            chapter_total=chapter_total,
        )
        if not extra:
            already_fallback = sum(1 for item in quizzes if quiz_is_compiled_fallback(item))
            fallback_budget = min(chunk, max(0, 2 - already_fallback))
            if fallback_budget <= 0:
                _fail_local_assess(
                    "quizzes",
                    chapter,
                    f"required {count} distinct questions, but only {len(quizzes)} are usable",
                )
            extra = quizzes_from_chapter_theory(
                chapter=chapter,
                theory=theory_blob,
                count=fallback_budget,
                topic_key=topic_key,
                locale=locale,
                start_index=len(quizzes) + 1,
                already=all_seen_questions,
            )
            if extra:
                reason = (
                    "after LLM repeated already-used stems"
                    if duplicate_only
                    else "after LLM returned no usable JSON"
                )
                warnings.append(f"local quizzes: compiled from chapter theory {reason}")
                logger.warning("%s [%s]", warnings[-1], topic_key)
            else:
                _fail_local_assess(
                    "quizzes",
                    chapter,
                    f"required {count} distinct questions, but only {len(quizzes)} are usable",
                )
        quizzes.extend(extra)
        if persist is not None:
            persist(quizzes[:count])
    return quizzes[:count]


def _quiz_question_history(
    course_seen: list[str],
    quizzes: list[dict[str, object]],
) -> tuple[list[str], list[str]]:
    generated = [str(item.get("question") or "") for item in quizzes]
    prompt_questions = [
        *course_seen,
        *[
            question
            for question, quiz in zip(generated, quizzes, strict=True)
            if not quiz_is_compiled_fallback(quiz)
        ],
    ]
    return prompt_questions, [*course_seen, *generated]


async def _new_quiz_chunk(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    theory: dict[str, object],
    policy: LocalCoursePolicy,
    topic_key: str,
    chunk: int,
    start_index: int,
    prompt_questions: list[str],
    all_seen_questions: list[str],
    article_seeds: str,
    prior_digest: str,
    chapter_index: int,
    chapter_total: int,
) -> tuple[list[dict[str, object]], bool]:
    request_chunk = partial(
        _quiz_chunk,
        client,
        target,
        body=body,
        chapter=chapter,
        theory=theory,
        policy=policy,
        topic_key=topic_key,
        chunk=chunk,
        start_index=start_index,
        already_questions=prompt_questions,
        article_seeds=article_seeds,
        prior_digest=prior_digest,
        chapter_index=chapter_index,
        chapter_total=chapter_total,
    )
    extra = await request_chunk()
    if not extra:
        return [], False
    filtered = _drop_repeated_stems(extra, seen=all_seen_questions)
    if filtered:
        return filtered, False
    logger.warning(
        "quiz stems duplicated prior questions [%s]; retrying with novelty nudge",
        topic_key,
    )
    retried = await request_chunk(
        novelty_nudge=(
            "CRITICAL: previous JSON repeated an already-used stem. "
            "Invent a completely different question that still cites this chapter."
        ),
    )
    return _drop_repeated_stems(retried, seen=all_seen_questions), True


def _drop_repeated_stems(
    quizzes: list[dict[str, object]],
    *,
    seen: list[str],
) -> list[dict[str, object]]:

    known = [quiz_stem_key(question) for question in seen if question.strip()]
    kept: list[dict[str, object]] = []
    for quiz in quizzes:
        stem = quiz_stem_key(str(quiz.get("question") or ""))
        if not stem:
            continue
        if any(
            stem == earlier or quiz_stems_overlap(stem, earlier) >= _STEM_REPEAT_OVERLAP
            for earlier in known
        ):
            continue
        known.append(stem)
        kept.append(quiz)
    return kept


def quiz_is_compiled_fallback(quiz: dict[str, object]) -> bool:
    return bool(re.search(r"-quiz-g\d+$", str(quiz.get("id") or "")))


async def generate_topic_practice(
    client: httpx.AsyncClient,
    target: LlmTarget,
    *,
    body: CourseFromArticleRequest,
    chapter: dict[str, str],
    theory: dict[str, object],
    count: int,
    policy: LocalCoursePolicy,
    topic_key: str,
    warnings: list[str],
    already: list[dict[str, object]] | None = None,
    persist: Callable[[list[dict[str, object]]], None] | None = None,
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> list[dict[str, object]]:
    if count <= 0 or not getattr(body, "include_code", True):
        return []
    article_seeds = _article_seed_block(exercise_seeds, kinds=("practice", "open"))
    locale = _body_locale(body)
    theory_blob = str(theory.get("content") or "")
    runtime = str(body.runtime or "").strip() or detect_practice_runtime(theory_blob) or "python"
    tasks: list[dict[str, object]] = []
    for item in already or []:
        normalized = normalize_practice_task(item, theory=theory_blob)
        if practice_spec_is_usable(normalized, locale=locale, theory=theory_blob, runtime=runtime):
            tasks.append(normalized)
    tasks = tasks[:count]
    batch = max(1, policy.practice_batch_size)
    while len(tasks) < count:
        chunk = min(batch, count - len(tasks))
        extra = await _practice_chunk(
            client,
            target,
            body=body,
            chapter=chapter,
            theory=theory,
            policy=policy,
            topic_key=topic_key,
            chunk=chunk,
            start_index=len(tasks) + 1,
            already_titles=[str(item.get("title") or "") for item in tasks],
            article_seeds=article_seeds,
            runtime=runtime,
        )
        if not extra:
            extra = practice_from_chapter_theory(
                chapter=chapter,
                theory=theory_blob,
                count=chunk,
                topic_key=topic_key,
                locale=locale,
                runtime=runtime,
                start_index=len(tasks) + 1,
            )
            if extra:
                warnings.append(
                    "local practice: compiled from chapter theory after LLM returned no usable JSON"
                )
                logger.warning("%s [%s]", warnings[-1], topic_key)
            elif tasks:
                warnings.append(
                    f"local practice: chapter «{chapter.get('title')}» kept "
                    f"{len(tasks)} of {count} tasks — theory ran out of distinct steps"
                )
                logger.warning("%s [%s]", warnings[-1], topic_key)
                break
            else:
                _fail_local_assess(
                    "practice",
                    chapter,
                    "chapter theory is too thin to compile practice",
                )
        tasks.extend(extra)
        if persist is not None:
            persist(tasks[:count])
    return tasks[:count]
