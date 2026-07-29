from __future__ import annotations

import json

from studio_contracts.studio_schemas import CourseFromArticleRequest


def _quizzes_user_message(
    body: CourseFromArticleRequest,
    *,
    outcomes: list[str],
    chapters: list[dict[str, str]],
    theory_steps: list[dict[str, object]],
) -> str:
    chapter_titles = [c["title"] for c in chapters]
    theory_digest = "\n\n".join(
        f"### {step.get('title')}\n{str(step.get('content') or '')[:900]}"
        for step in theory_steps[:6]
    )
    return "\n\n".join(
        [
            "## Stage\nquizzes",
            f"## Locale\n{body.locale}",
            f"## Quiz count\n{body.quiz_count}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps(chapter_titles, ensure_ascii=False)}",
            f"## Theory digest\n{theory_digest[:8000]}",
            '## Output\nJSON {"quizzes":[...]} with answer indices.',
        ]
    )


def _quiz_one_user_message(
    body: CourseFromArticleRequest,
    *,
    outcomes: list[str],
    chapters: list[dict[str, str]],
    theory_steps: list[dict[str, object]],
    index: int,
    prior_titles: list[str],
) -> str:
    chapter_titles = [c["title"] for c in chapters]
                                                                               
    focus = theory_steps[index % len(theory_steps)] if theory_steps else None
    focus_block = ""
    if focus is not None:
        focus_block = (
            f"### {focus.get('title')}\n{str(focus.get('content') or '')[:1400]}"
        )
    prior = ", ".join(prior_titles) if prior_titles else "(none yet)"
    return "\n\n".join(
        part
        for part in [
            "## Stage\nquizzes",
            f"## Locale\n{body.locale}",
            f"## Quiz position\n{index + 1}/{body.quiz_count}",
            f"## Already created titles\n{prior}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps(chapter_titles, ensure_ascii=False)}",
            f"## Focus theory\n{focus_block}" if focus_block else "",
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
) -> str:
    return "\n\n".join(
        [
            "## Stage\ncode_ladder",
            f"## Locale\n{body.locale}",
            f"## Runtime\n{body.runtime} {body.runtime_version}",
            f"## Task count\n{body.code_count}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps([c['title'] for c in chapters], ensure_ascii=False)}",
            '## Output\nJSON {"tasks":[...]} easy→hard with template+tests.',
            "If a task cannot run as pure JSON I/O + setup stubs, set checker=llm and rubric.",
        ]
    )


def _code_one_task_user_message(
    body: CourseFromArticleRequest,
    *,
    outcomes: list[str],
    chapters: list[dict[str, str]],
    level: str,
    index: int,
    prior_titles: list[str],
) -> str:
    prior = ", ".join(prior_titles) if prior_titles else "(none yet)"
    return "\n\n".join(
        [
            "## Stage\ncode_ladder",
            f"## Locale\n{body.locale}",
            f"## Runtime\n{body.runtime} {body.runtime_version}",
            f"## Level\n{level}",
            f"## Ladder position\n{index + 1}/{body.code_count}",
            f"## Already created titles\n{prior}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps([c['title'] for c in chapters], ensure_ascii=False)}",
            "## Output\n"
            'ONE JSON object: either {"task":{...}} or {"tasks":[{...}]} '
            "with a single code task for this level only "
            "(title, content, template, tests, entrypoint). "
            "Do not emit other levels. "
            "If tests cannot run as pure JSON I/O, set checker=llm and rubric.",
        ]
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
            f"## Locale\n{body.locale}",
            f"## Task count\n{body.code_count}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps([c['title'] for c in chapters], ensure_ascii=False)}",
            '## Output\nJSON {"tasks":[...]} kind=task with content+rubric (easy→hard).',
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
            f"## Locale\n{body.locale}",
            f"## Level\n{level}",
            f"## Ladder position\n{index + 1}/{body.code_count}",
            f"## Already created titles\n{prior}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Chapters\n{json.dumps([c['title'] for c in chapters], ensure_ascii=False)}",
            "## Output\n"
            'ONE JSON object: either {"task":{...}} or {"tasks":[{...}]} '
            "with a single open task for this level only "
            "(title, content, rubric, optional exemplar). Do not emit other levels.",
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
            f"## Locale\n{body.locale}",
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
            f"## Locale\n{body.locale}",
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
