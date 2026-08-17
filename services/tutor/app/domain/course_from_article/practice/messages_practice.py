from __future__ import annotations

import json

from app.domain.course_from_article.curriculum.outline.course_locale import locale_prompt_block
from app.domain.course_from_article.practice.source_exercise_harvest import HarvestedExercise
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


def _quiz_one_user_message(
    body: CourseFromArticleRequest,
    *,
    outcomes: list[str],
    chapters: list[dict[str, str]],
    theory_steps: list[dict[str, object]],
    index: int,
    prior_titles: list[str],
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> str:
    chapter_titles = [c["title"] for c in chapters]

    focus = theory_steps[index % len(theory_steps)] if theory_steps else None
    focus_block = ""
    if focus is not None:
        focus_block = f"### {focus.get('title')}\n{str(focus.get('content') or '')[:1800]}"
    chapter = chapters[index % len(chapters)] if chapters else {}
    objective = str(chapter.get("learning_objective") or "").strip()
    chapter_index = index % len(chapters) if chapters else 0
    spacing = (
        "One item should apply an earlier chapter's idea inside THIS chapter's "
        "situation (not a recap of the earlier title)."
        if chapter_index > 0
        else ""
    )
    prior = ", ".join(prior_titles) if prior_titles else "(none yet)"
    quiz_seeds = [item for item in (exercise_seeds or []) if item.kind in {"quiz", "open"}]
    seed_block = ""
    if quiz_seeds:
        seed = quiz_seeds[index % len(quiz_seeds)]
        seed_block = (
            "## Prefer this article check as the basis\n"
            f"{seed.as_prompt_block()}\n"
            "Adapt into ONE fair MCQ (4 choices). Do not invent unrelated trivia."
        )
    return "\n\n".join(
        part
        for part in [
            "## Stage\nquizzes",
            locale_prompt_block(body.locale),
            f"## Quiz position\n{index + 1}/{body.quiz_count}",
            f"## Already created titles\n{prior}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps(chapter_titles, ensure_ascii=False)}",
            f"## Focus theory\n{focus_block}" if focus_block else "",
            f"## Learning objective\n{objective}" if objective else "",
            f"## Spacing\n{spacing}" if spacing else "",
            seed_block,
            "## Output\n"
            'ONE JSON object: either {"quiz":{...}} or {"quizzes":[{...}]} '
            "with a single MCQ (title, question, choices[4], answer index). "
            "Do not emit other quizzes.",
        ]
        if part
    )


def _code_one_task_user_message(
    body: CourseFromArticleRequest,
    *,
    outcomes: list[str],
    chapters: list[dict[str, str]],
    level: str,
    index: int,
    prior_titles: list[str],
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> str:
    prior = ", ".join(prior_titles) if prior_titles else "(none yet)"
    practice_seeds = [item for item in (exercise_seeds or []) if item.kind in {"practice", "open"}]
    seed_block = ""
    if practice_seeds:
        seed = practice_seeds[index % len(practice_seeds)]
        seed_block = (
            "## Prefer this article lab as the basis\n"
            f"{seed.as_prompt_block()}\n"
            "Rewrite as a graded practice brief (Input/Output/Constraints). "
            "Keep the article's intent; do not invent unrelated tools."
        )
    chapter_hint = ""
    if chapters:
        focus = chapters[index % len(chapters)]
        excerpt = (focus.get("source_excerpt") or "")[:900]
        objective = str(focus.get("learning_objective") or "").strip()
        chapter_hint = f"## Focus chapter\n{focus['title']}\n{excerpt}"
        if objective:
            chapter_hint += f"\n\nLearning objective: {objective}"
    return "\n\n".join(
        part
        for part in [
            "## Stage\ncode_ladder",
            locale_prompt_block(body.locale),
            f"## Runtime\n{body.runtime} {body.runtime_version}",
            f"## Level\n{level}",
            f"## Ladder position\n{index + 1}/{body.code_count}",
            "## Same-skill ladder\n"
            "Stay on the focus chapter skill; harder levels fade scaffold — "
            "do not invent APIs from later chapters.",
            f"## Already created titles\n{prior}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps([c['title'] for c in chapters], ensure_ascii=False)}",
            chapter_hint,
            seed_block,
            "## Output\n"
            'ONE JSON object: either {"task":{...}} or {"tasks":[{...}]} '
            "with a single code task for this level only "
            "(title, content, template, tests, entrypoint, optional dependencies[]). "
            "Put third-party packages in dependencies[], not in content. "
            "Do not emit other levels. "
            "Write content as a readable brief with Input / Output / Constraints "
            "so the learner does not rely only on the docstring. "
            "If tests cannot run as pure JSON I/O, set checker=llm and rubric. "
            "When the source teaches a configuration artifact or shell workflow, "
            "use kind=task and request that native artifact or command sequence — "
            "never wrap its text in an unrelated programming function.",
        ]
        if part
    )


def _task_one_user_message(
    body: CourseFromArticleRequest,
    *,
    outcomes: list[str],
    chapters: list[dict[str, str]],
    domain: str,
    level: str,
    index: int,
    prior_titles: list[str],
) -> str:
    prior = ", ".join(prior_titles) if prior_titles else "(none yet)"
    return "\n\n".join(
        [
            "## Stage\ntask_ladder",
            f"## Domain\n{domain}",
            locale_prompt_block(body.locale),
            f"## Level\n{level}",
            f"## Ladder position\n{index + 1}/{body.code_count}",
            "## Same-skill ladder\n"
            "Same chapter skill; harder levels fade scaffold — not a new topic.",
            f"## Already created titles\n{prior}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps([c['title'] for c in chapters], ensure_ascii=False)}",
            "## Output\n"
            'ONE JSON object: either {"task":{...}} or {"tasks":[{...}]} '
            "with a single open task for this level only "
            "(title, content, rubric, optional exemplar). Do not emit other levels. "
            "content must clearly list goal, accepted input/materials, "
            "expected deliverable, and constraints.",
        ]
    )


def _polish_one_user_message(
    body: CourseFromArticleRequest,
    *,
    chapters: list[dict[str, str]],
    book_spine: dict[str, str],
    digest: dict[str, object],
    index: int,
    total: int,
) -> str:
    syllabus = "\n".join(f"{i + 1}. {item['title']}" for i, item in enumerate(chapters))
    spine = book_spine or {}
    spine_block = "\n".join(
        part
        for part in [
            f"voice: {spine['voice']}" if spine.get("voice") else "",
            f"address: {spine['address']}" if spine.get("address") else "",
            f"throughline: {spine['throughline']}" if spine.get("throughline") else "",
            f"glossary: {spine['glossary']}" if spine.get("glossary") else "",
            f"metaphors: {spine['metaphors']}" if spine.get("metaphors") else "",
        ]
        if part
    )
    opening_block = "\n".join(
        [
            f"### {digest['id']} — {digest['title']}",
            f"opening_chars={digest['opening_chars']}",
            "<opening>",
            str(digest["opening"]),
            "</opening>",
        ]
    )
    return "\n\n".join(
        part
        for part in [
            "## Stage\nbook_polish",
            locale_prompt_block(body.locale),
            f"## Chapter position\n{index + 1}/{total}",
            f"## Book spine\n{spine_block}" if spine_block else "",
            f"## Full syllabus ({len(chapters)} chapters)\n{syllabus}",
            "## Chapter opening to edit (keep the rest of this chapter)\n" + opening_block,
            "## Editorial brief\n"
            "Unify voice/address with the spine for THIS chapter only. "
            "Prefer `opening` edit. Use full `content` only when necessary. "
            "Do not invent APIs. Empty edits is fine.",
            "## Output\n"
            'ONE JSON object: {"edits":[{"id":"'
            + str(digest["id"])
            + '","opening":"..."}]} with at most one edit for this chapter.',
        ]
        if part
    )
