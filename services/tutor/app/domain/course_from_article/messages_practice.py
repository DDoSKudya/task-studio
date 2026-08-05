from __future__ import annotations

import json

from studio_contracts.studio_schemas import CourseFromArticleRequest

from .course_locale import locale_prompt_block
from .source_exercise_harvest import (
    HarvestedExercise,
    exercises_to_prompt_digest,
)


def _quizzes_user_message(
    body: CourseFromArticleRequest,
    *,
    outcomes: list[str],
    chapters: list[dict[str, str]],
    theory_steps: list[dict[str, object]],
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> str:
    chapter_titles = [c["title"] for c in chapters]
    theory_digest = "\n\n".join(
        f"### {step.get('title')}\n{str(step.get('content') or '')[:1200]}"
        for step in theory_steps[:8]
    )
    seeds = exercises_to_prompt_digest(
        exercise_seeds or [],
        kinds={"quiz", "open", "answer_key"},
        limit=8,
        char_budget=5_000,
    )
    return "\n\n".join(
        part
        for part in [
            "## Stage\nquizzes",
            locale_prompt_block(body.locale),
            f"## Quiz count\n{body.quiz_count}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps(chapter_titles, ensure_ascii=False)}",
            f"## Theory digest\n{theory_digest[:10_000]}",
            (
                "## Harvested article checks (prefer adapting these)\n"
                f"{seeds}\n"
                "Turn article quizzes/open questions into fair MCQs; "
                "use answer_key only to set the correct choice index — "
                "never paste answers into the question text."
                if seeds
                else ""
            ),
            '## Output\nJSON {"quizzes":[...]} with answer indices.',
        ]
        if part
    )


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
            seed_block,
            "## Output\n"
            'ONE JSON object: either {"quiz":{...}} or {"quizzes":[{...}]} '
            "with a single MCQ (title, question, choices[4], answer index). "
            "Do not emit other quizzes.",
        ]
        if part
    )


def _code_user_message(
    body: CourseFromArticleRequest,
    *,
    outcomes: list[str],
    chapters: list[dict[str, str]],
    exercise_seeds: list[HarvestedExercise] | None = None,
) -> str:
    seeds = exercises_to_prompt_digest(
        exercise_seeds or [],
        kinds={"practice", "open"},
        limit=6,
        char_budget=5_000,
    )
    chapter_support = "\n".join(
        f"- {c['title']}: {(c.get('source_excerpt') or '')[:400]}" for c in chapters[:8]
    )
    return "\n\n".join(
        part
        for part in [
            "## Stage\ncode_ladder",
            locale_prompt_block(body.locale),
            f"## Runtime\n{body.runtime} {body.runtime_version}",
            f"## Task count\n{body.code_count}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps([c['title'] for c in chapters], ensure_ascii=False)}",
            f"## Chapter source hints\n{chapter_support}" if chapter_support.strip() else "",
            (
                "## Harvested article labs (prefer adapting into ТЗ)\n"
                f"{seeds}\n"
                "Turn article labs into clear briefs with Input/Output/Constraints."
                if seeds
                else ""
            ),
            '## Output\nJSON {"tasks":[...]} easy→hard with template+tests.',
            "Each task may include machine field dependencies: string[] (pip/npm specs). "
            "Never paste requirements.txt/package.json examples into content.",
            "Each task.content must be a clear brief: goal, Input (args/types/examples), "
            "Output (return fields), Constraints — not only a one-line hint. "
            "If a task cannot run as pure JSON I/O + setup stubs, set checker=llm and rubric.",
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
            "For Docker/CLI/DevOps labs: use kind=task (paste Dockerfile/commands) — "
            "never a Python function that returns Dockerfile text.",
        ]
        if part
    )


def _task_user_message(
    body: CourseFromArticleRequest,
    *,
    outcomes: list[str],
    chapters: list[dict[str, str]],
    domain: str,
) -> str:
    return "\n\n".join(
        [
            "## Stage\ntask_ladder",
            f"## Domain\n{domain}",
            locale_prompt_block(body.locale),
            f"## Task count\n{body.code_count}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps([c['title'] for c in chapters], ensure_ascii=False)}",
            '## Output\nJSON {"tasks":[...]} kind=task with content+rubric (easy→hard).',
            "Each content brief must state goal, accepted materials/input, "
            "expected deliverable, and constraints.",
        ]
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


def _polish_user_message(
    body: CourseFromArticleRequest,
    *,
    chapters: list[dict[str, str]],
    book_spine: dict[str, str],
    digests: list[dict[str, object]],
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
    chapter_blocks = []
    for item in digests:
        chapter_blocks.append(
            "\n".join(
                [
                    f"### {item['id']} — {item['title']}",
                    f"opening_chars={item['opening_chars']}",
                    "<opening>",
                    str(item["opening"]),
                    "</opening>",
                ]
            )
        )
    return "\n\n".join(
        part
        for part in [
            "## Stage\nbook_polish",
            locale_prompt_block(body.locale),
            f"## Book spine\n{spine_block}" if spine_block else "",
            f"## Full syllabus ({len(chapters)} chapters)\n{syllabus}",
            "## Chapter openings (edit these; keep the rest of each chapter)\n"
            + "\n\n".join(chapter_blocks),
            "## Editorial brief\n"
            "Unify voice/address with the spine. Strengthen bridges. "
            "Kill repeated intros and re-definitions of earlier chapters. "
            "Prefer `opening` edits. Use full `content` only when necessary. "
            "Do not invent APIs. Empty edits is fine.",
            '## Output\nJSON {"edits":[{"id":"...","opening":"..."}]}.',
        ]
        if part
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
