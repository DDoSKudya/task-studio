from __future__ import annotations

import json

from studio_contracts.studio_schemas import CourseFromArticleRequest

from .constants import _MAX_CHAPTERS, _MAX_CHAPTERS_COMPACT
from .course_locale import locale_prompt_block


def _analyze_user_message(
    body: CourseFromArticleRequest,
    article: str,
    *,
    sources: list[dict[str, object]] | None = None,
    compact: bool = False,
) -> str:
    source_rows = sources or []
    multi = len(source_rows) > 1
    source_catalog = "\n".join(
        f"- Source {index}: {item['title']} ({len(str(item['content']))} chars)"
        for index, item in enumerate(source_rows, start=1)
    )
    process = (
        "1) Inventory concepts from EVERY source — prioritize teaching substance, "
        "not homework blocks.\n"
        "2) Deduplicate overlaps into shared course topics.\n"
        "3) Order by learning dependency: foundations → core → depth → traps.\n"
        "4) Name chapters for the course (not for a single article file).\n"
        "5) Attach verbatim source_excerpt + source_titles per chapter "
        "(teaching prose only; skip assignment/quiz sections).\n"
        "6) Emit book_spine (voice, address, throughline, glossary, metaphors) "
        "so theory chapters read as one book.\n"
        "7) Per chapter: bridge_from_prev, assumes_known, must_not_reteach, learning_objective.\n"
        "8) Embedded article quizzes/labs are NOT theory chapters — "
        "they become assess/practice later; do not outline them as study slides."
    )
    wanted = body.effective_theory_count()
    hard_max = _MAX_CHAPTERS_COMPACT if compact else _MAX_CHAPTERS
    target = min(max(1, int(wanted or hard_max)), hard_max)
    corpus_chars = len(article)
    supports_target = corpus_chars >= target * 2_500
    constraints = [
        f"Target theory chapters (slides): {target} (hard max {hard_max}).",
        (
            f"Corpus length is {corpus_chars} characters — "
            + (
                f"aim for about {target} distinct slides; split only where the material "
                "has real pedagogical beats (not micro-slides)."
                if supports_target
                else "prefer as many distinct chapters as the material honestly supports, "
                f"up to {target}; do not invent empty filler."
            )
        ),
        "One idea per chapter — merge tiny fragments, split only dense sections.",
        "Course title must describe the whole subject, not only the deepest subtopic.",
        "The syllabus must feel like one authored book, not a stack of article dumps.",
        "Preserve article meaning: chapter titles and excerpts must cover the real "
        "concepts/examples from the sources — do not thin them into generic fluff.",
        "Never turn article 'Задание' / Exercise / Quiz sections into theory chapters.",
    ]
    if compact:
        constraints.append(
            "Local model mode: keep chapters dense and complete; still aim for the target count."
        )
    if multi:
        constraints.extend(
            [
                f"You have {len(source_rows)} sources — each must appear in at least one chapter "
                "(unless pure duplicate).",
                "Do NOT follow upload order if foundations appear in a later source.",
                "Never open the syllabus on an advanced pattern while a foundation source exists.",
            ]
        )
    else:
        constraints.append("Prefer TOC headings, then finer pedagogical splits.")

    return "\n\n".join(
        part
        for part in [
            "## Stage\nanalyze",
            "## Role\nCurriculum architect synthesizing source article(s) into one course.",
            locale_prompt_block(body.locale),
            (
                "## Audience\n"
                + (body.audience or "beginners and intermediate developers who need mental models")
            ),
            f"## Preferred title\n{body.title or '(derive a course-level title from all sources)'}",
            f"## Sources catalog\n{source_catalog or '- (single corpus below)'}",
            "## Constraints\n" + "\n".join(f"- {item}" for item in constraints),
            f"## Process\n{process}",
            f"## Source corpus\n<source_corpus>\n{article}\n</source_corpus>",
            "## Output\nJSON skeleton only: pack_id, title, audience_level, domain, "
            "outcomes, book_spine, chapters[{id,title}]. "
            f"Field locale is fixed by the request ({body.locale}) — omit or echo it exactly. "
            "Do NOT include long source_excerpt yet — chapter details are filled next.",
        ]
        if part
    )


def _expand_outline_user_message(
    body: CourseFromArticleRequest,
    article: str,
    *,
    chapters: list[dict[str, str]],
    target: int,
) -> str:
    existing = "\n".join(
        f"{index + 1}. {item.get('id')}: {item.get('title')}" for index, item in enumerate(chapters)
    )
    return "\n\n".join(
        [
            "## Stage\nanalyze_expand",
            "## Role\nExpand a thin syllabus into the requested slide count.",
            locale_prompt_block(body.locale),
            f"## Target chapter count\n{target}",
            f"## Current chapters ({len(chapters)})\n{existing}",
            "## Rules\n"
            f"- Return EXACTLY {target} chapters as JSON "
            '{"chapters":[{"id","title"},...]}.\n'
            "- Split dense current chapters into finer pedagogical beats.\n"
            "- Keep learning order; do not drop foundations.\n"
            "- Do not invent topics absent from the corpus.\n"
            "- Titles must stay specific and non-duplicative.",
            f"## Source corpus\n<source_corpus>\n{article}\n</source_corpus>",
            '## Output\nJSON {"chapters":[{"id","title"},...]} only.',
        ]
    )


def _analyze_chapter_user_message(
    body: CourseFromArticleRequest,
    article: str,
    *,
    sources: list[dict[str, object]] | None,
    chapter: dict[str, str],
    index: int,
    total: int,
    outcomes: list[str],
) -> str:
    source_rows = sources or []
    source_catalog = "\n".join(
        f"- Source {i}: {item['title']}" for i, item in enumerate(source_rows, start=1)
    )
    return "\n\n".join(
        part
        for part in [
            "## Stage\nanalyze",
            "## Role\nFill details for ONE syllabus chapter only.",
            locale_prompt_block(body.locale),
            f"## Chapter position\n{index + 1}/{total}",
            f"## Chapter id\n{chapter.get('id') or ''}",
            f"## Chapter title\n{chapter.get('title') or ''}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Sources catalog\n{source_catalog or '- (corpus below)'}",
            f"## Source corpus\n<source_corpus>\n{article}\n</source_corpus>",
            "## Output\n"
            "ONE JSON object for this chapter only: "
            '{"chapter":{"id","title","purpose","learning_objective","bridge_from_prev","assumes_known",'
            '"must_not_reteach","source_titles","source_excerpt"}} '
            "OR the chapter fields at the top level. "
            "source_excerpt ≤ 3500 characters of verbatim TEACHING prose "
            "(skip homework/quiz/answer sections). Do not emit other chapters.",
        ]
        if part
    )


def _consistency_user_message(
    body: CourseFromArticleRequest,
    sources: list[dict[str, object]],
) -> str:
    blocks = []
    for index, item in enumerate(sources, start=1):
        excerpt = str(item["content"])[:4000]
        blocks.append(f'<source index="{index}" title="{item["title"]}">\n{excerpt}\n</source>')
    return "\n\n".join(
        [
            "## Stage\nconsistency",
            locale_prompt_block(body.locale),
            "## Task\n"
            "Judge whether these articles fit one course. List factual/API contradictions only.",
            "<sources>\n" + "\n\n".join(blocks) + "\n</sources>",
            "## Output\nJSON {related, similarity, shared_topic, deviations[]}.",
        ]
    )


def _theory_user_message(
    chapter: dict[str, str],
    body: CourseFromArticleRequest,
    outcomes: list[str],
    *,
    chapters: list[dict[str, str]],
    index: int,
    book_spine: dict[str, str] | None = None,
) -> str:
    return _theory_shared_context(
        chapter,
        body,
        outcomes,
        chapters=chapters,
        index=index,
        book_spine=book_spine,
        output="## Output\nJSON theory step (id/kind/title/content).",
    )


def _theory_meta_user_message(
    chapter: dict[str, str],
    body: CourseFromArticleRequest,
    outcomes: list[str],
    *,
    chapters: list[dict[str, str]],
    index: int,
    book_spine: dict[str, str] | None = None,
) -> str:
    return _theory_shared_context(
        chapter,
        body,
        outcomes,
        chapters=chapters,
        index=index,
        book_spine=book_spine,
        output=(
            "## Output\nJSON with id, kind, title ONLY. "
            "Do not include content — markdown body is generated in the next step."
        ),
    )


def _theory_content_user_message(
    chapter: dict[str, str],
    body: CourseFromArticleRequest,
    outcomes: list[str],
    *,
    chapters: list[dict[str, str]],
    index: int,
    book_spine: dict[str, str] | None = None,
    title: str | None = None,
    compact: bool = False,
) -> str:
    chapter_title = title or chapter["title"]
    if compact:
        output = (
            "## Output\nPlain markdown for this chapter only. "
            "Write one complete lesson: mental model, worked example, traps, recap — "
            "each section once, no repetition. "
            "Skip mermaid unless essential. Prefer source substance over padding."
        )
    else:
        output = (
            "## Output\nPlain markdown for this chapter only. "
            "Write the full teaching content the learner needs — do not truncate on purpose. "
            "If the answer hits a length limit, stop cleanly; a continue pass will follow."
        )
    return _theory_shared_context(
        chapter,
        body,
        outcomes,
        chapters=chapters,
        index=index,
        book_spine=book_spine,
        chapter_title=chapter_title,
        output=output,
        compact=compact,
    )


def _theory_shared_context(
    chapter: dict[str, str],
    body: CourseFromArticleRequest,
    outcomes: list[str],
    *,
    chapters: list[dict[str, str]],
    index: int,
    book_spine: dict[str, str] | None = None,
    output: str,
    chapter_title: str | None = None,
    compact: bool = False,
) -> str:
    syllabus = "\n".join(f"{i + 1}. {item['title']}" for i, item in enumerate(chapters))
    prev_title = chapters[index - 1]["title"] if index > 0 else "(course start)"
    next_title = chapters[index + 1]["title"] if index + 1 < len(chapters) else "(course end)"
    purpose = chapter.get("purpose") or ""
    learning_objective = chapter.get("learning_objective") or ""
    source_titles = chapter.get("source_titles") or ""
    bridge = chapter.get("bridge_from_prev") or ""
    assumes = chapter.get("assumes_known") or ""
    must_not = chapter.get("must_not_reteach") or ""
    source_images = chapter.get("source_images") or ""
    spine = book_spine or {}
    audience = body.audience or (
        "beginners: mental models first, then jargon; little prior knowledge of this topic"
    )
    if compact:
        writing_brief = (
            "Write this chapter as part of ONE book, not a stub. "
            "Teach ONLY this chapter title — cover the source ideas that belong here. "
            "Assume prior syllabus chapters were read; do not re-teach them. "
            "Beginner-friendly prose: mental model + worked example + traps + short recap. "
            "Each heading/section appears once — never loop or paste the lesson again. "
            "Ground claims in the source excerpt; expand the article's meaning — "
            "do not replace it with generic filler that ignores the source. "
            "Worked examples may show commands/code from the article, but NEVER add "
            "homework blocks, 'Задание N', quizzes, check-yourself, or answer keys. "
            "Reuse book_spine voice/throughline/glossary when present. "
            "Locale Russian → natural Russian wording "
            "(компьютерное зрение), not Latin-Cyrillic mashups."
        )
    else:
        writing_brief = (
            "Write this chapter as part of ONE book, not a standalone essay. "
            "Teach ONLY this chapter title — one idea. "
            "Assume prior syllabus chapters were read; "
            "do not re-teach them. "
            "Beginner-friendly literary prose: "
            "mental model + worked example + traps. "
            "Preserve the article's conceptual spine: definitions, contrasts, "
            "and real examples from the excerpt must survive into the chapter. "
            "If the excerpt is thin, fill pedagogical gaps without inventing APIs. "
            "For foundation/architecture/flow chapters, include one ```mermaid diagram. "
            "Plain markdown code fences (no HTML / highlighter tokens). "
            "Fence tags must match the body: Python/SQLAlchemy → ```python, raw SQL → ```sql, "
            "diagrams → ```mermaid. "
            "Never label `with Session(...) as session:` as sql. "
            "Never include homework, lab assignments, numbered tasks for the learner, "
            "MCQ quizzes, 'Проверьте себя', or answer keys — assess/practice stages own those. "
            "When Source figures are listed, embed at most 1–2 as exact markdown images "
            "if they clarify this chapter; never invent image URLs. "
            "Reuse book_spine voice/throughline/glossary; open with bridge_from_prev when present."
        )
    spine_block = ""
    if any(spine.get(key) for key in ("voice", "address", "throughline", "glossary", "metaphors")):
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
    excerpt = chapter.get("source_excerpt") or ""
    if compact and len(excerpt) > 4_200:
        excerpt = excerpt[:4_200].rstrip() + "…"
    shown_title = chapter_title or chapter["title"]
    return "\n\n".join(
        part
        for part in [
            "## Stage\ntheory_chapter",
            locale_prompt_block(body.locale),
            f"## Audience\n{audience}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Book spine\n{spine_block}" if spine_block else "",
            f"## Full syllabus ({len(chapters)} chapters)\n{syllabus}",
            f"## This chapter\n{index + 1}/{len(chapters)}: {shown_title}",
            f"## Previous chapter\n{prev_title}",
            f"## Next chapter\n{next_title}",
            f"## Bridge from previous\n{bridge}" if bridge else "",
            f"## Assumes known\n{assumes}" if assumes else "",
            f"## Must not reteach\n{must_not}" if must_not else "",
            f"## Chapter purpose\n{purpose}" if purpose else "",
            f"## Learning objective\n{learning_objective}" if learning_objective else "",
            f"## Source titles for this chapter\n{source_titles}" if source_titles else "",
            f"## Chapter id\n{chapter['id']}",
            f"## Source excerpt\n<source_excerpt>\n{excerpt}\n</source_excerpt>",
            (
                "## Source figures (optional)\n"
                "Embed at most 1–2 lines EXACTLY as given when they illustrate this chapter. "
                "Do not invent URLs.\n"
                f"{source_images}"
                if source_images
                else ""
            ),
            f"## Writing brief\n{writing_brief}",
            output,
        ]
        if part
    )
