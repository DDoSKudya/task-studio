from __future__ import annotations

import json

from app.domain.course_from_article.common.content.constants import (
    _MAX_CHAPTERS,
    _MAX_CHAPTERS_COMPACT,
)
from app.domain.course_from_article.curriculum.outline.chapter_budget import (
    chapter_ceiling,
    chapter_floor,
    corpus_char_count,
)
from app.domain.course_from_article.curriculum.outline.course_locale import locale_prompt_block
from studio_contracts.api.studio_schemas import CourseFromArticleRequest


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
        "3) Order: chapter 1 = simplest complete whole-task (epitome miniature a "
        "beginner can finish — not a glossary); then one added condition per chapter; "
        "name terms before the process that uses them.\n"
        "4) Name chapters for the course (not for a single article file).\n"
        "5) Attach verbatim source_excerpt + source_titles per chapter "
        "(teaching prose only; skip assignment/quiz sections).\n"
        "6) Emit book_spine (voice, address, throughline, glossary, metaphors) "
        "so theory chapters read as one book; throughline = the epitome story, "
        "not a TOC list.\n"
        "7) Per chapter: bridge_from_prev, assumes_known, must_not_reteach, learning_objective.\n"
        "8) Embedded article quizzes/labs are NOT theory chapters — "
        "they become assess/practice later; do not outline them as study slides."
    )
    hard_max = _MAX_CHAPTERS_COMPACT if compact else _MAX_CHAPTERS
    corpus_chars = corpus_char_count(source_rows, article)
    target = chapter_ceiling(body, corpus_chars=corpus_chars, hard_max=hard_max)
    floor = chapter_floor(body, corpus_chars=corpus_chars, ceiling=target)
    supports_target = corpus_chars >= target * 2_500
    constraints = [
        f"Chapter ceiling: {target} (hard max {hard_max}). This is a cap, not a quota.",
        (
            f"Chapter floor: {floor}. This corpus carries at least {floor} distinct teachable "
            "beats — returning fewer means you merged separate ideas, not that the sources "
            "are thin."
        ),
        (
            f"Corpus length is {corpus_chars} characters — "
            + (
                f"emit as many distinct teachable chapters as the sources support, "
                f"up to {target}; split only where the material has real pedagogical beats."
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
        "source_excerpt must be teaching prose copied from the source, never just "
        "the chapter title. One excerpt, one chapter idea.",
        "Never turn article 'Задание' / Exercise / Quiz sections into theory chapters.",
    ]
    if compact:
        constraints.append(
            "Local model mode: keep chapters dense and complete; do not pad to the ceiling."
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
    epitome = ""
    if index == 0:
        epitome = (
            "## Chapter 1 rule\n"
            "This is the epitome: source_excerpt and learning_objective must support "
            "one miniature complete working story the learner could finish after this "
            "chapter alone — not a glossary or 'what you will learn' dump.\n"
        )
    return "\n\n".join(
        part
        for part in [
            "## Stage\nanalyze",
            "## Role\nFill details for ONE syllabus chapter only.",
            locale_prompt_block(body.locale),
            f"## Chapter position\n{index + 1}/{total}",
            epitome,
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
    prior_chapter_digest: str = "",
) -> str:
    chapter_title = title or chapter["title"]
    if compact:
        output = (
            "## Output\nPlain markdown for this chapter only. "
            "Write one continuous textbook chapter: assertion headings, running prose, "
            "no boxed asides, no headings named Activation/Trap/Recap. Cover every named "
            "API or step in the excerpt; do not summarize the chapter into a blurb. "
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
        prior_chapter_digest=prior_chapter_digest,
    )


def _theory_section_user_message(
    chapter: dict[str, str],
    body: CourseFromArticleRequest,
    outcomes: list[str],
    *,
    chapters: list[dict[str, str]],
    index: int,
    section_excerpt: str,
    section_index: int,
    section_count: int,
    section_running_summary: str = "",
    prior_chapter_digest: str = "",
    book_spine: dict[str, str] | None = None,
) -> str:
    syllabus = "\n".join(f"{i + 1}. {item['title']}" for i, item in enumerate(chapters))
    must_not = chapter.get("must_not_reteach") or ""
    bridge = chapter.get("bridge_from_prev") or ""
    purpose = chapter.get("purpose") or ""
    learning_objective = chapter.get("learning_objective") or ""
    spine = book_spine or {}
    spine_bits = [
        f"voice: {spine['voice']}" if spine.get("voice") else "",
        f"throughline: {spine['throughline']}" if spine.get("throughline") else "",
    ]
    spine_block = "\n".join(bit for bit in spine_bits if bit)
    audience = body.audience or (
        "beginners: mental models first, then jargon; little prior knowledge of this topic"
    )
    return "\n\n".join(
        part
        for part in [
            "## Stage\ntheory_section",
            locale_prompt_block(body.locale),
            f"## Audience\n{audience}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Book spine\n{spine_block}" if spine_block else "",
            f"## Full syllabus ({len(chapters)} chapters)\n{syllabus}",
            f"## This chapter\n{index + 1}/{len(chapters)}: {chapter['title']}",
            f"## Section\n{section_index}/{section_count} of this chapter",
            f"## Bridge from previous chapter\n{bridge}" if bridge else "",
            (f"## Prior chapters digest\n{prior_chapter_digest}" if prior_chapter_digest else ""),
            (
                f"## Earlier sections in this chapter\n{section_running_summary}"
                if section_running_summary
                else ""
            ),
            f"## Must not reteach\n{must_not}" if must_not else "",
            f"## Chapter purpose\n{purpose}" if purpose else "",
            f"## Learning objective\n{learning_objective}" if learning_objective else "",
            f"## Chapter id\n{chapter['id']}",
            (
                "## Source excerpt for THIS section only\n"
                f"<source_excerpt>\n{section_excerpt.strip()}\n</source_excerpt>"
            ),
            "## Writing brief\n"
            "Write ONLY the teaching fragment for this section excerpt. "
            "The excerpt may be another language; write this fragment in the course locale. "
            "Ground claims in the excerpt; do not re-teach prior sections or syllabus chapters. "
            "Mental model and/or worked example and/or trap as the excerpt warrants — "
            "no homework, quizzes, or answer keys. "
            "Plain markdown; no preamble about being an AI. "
            "Do not restart the whole chapter; continue from earlier sections "
            "when a summary is given.",
            "## Output\nPlain markdown for this section only.",
        ]
        if part
    )


def _theory_writing_brief(*, compact: bool, is_first: bool) -> str:
    if compact:
        brief = (
            "Write this chapter as part of ONE book, not a stub. "
            "Teach ONLY this chapter title — cover the source ideas that belong here. "
            "Assume prior syllabus chapters were read; do not re-teach them. "
            "Open given→new: first sentences use what the prior chapter taught, "
            "then one new move. "
            "Beginner-friendly running prose: picture, then example, then the name; "
            "traps as sentences, not boxes. "
            "Each heading/section appears once — never loop or paste the lesson again. "
            "Ground claims in the source excerpt; expand the article's meaning — "
            "do not replace it with generic filler that ignores the source. "
            "Worked examples may show commands/code from the article, but NEVER add "
            "homework blocks, 'Задание N', quizzes, check-yourself, or answer keys. "
            "If quizzes/practice are OFF, do not add self-checks to compensate. "
            "Reuse book_spine voice/throughline/glossary when present. "
            "Write in the course locale, not the excerpt language. "
            "Keep API names; do not mix scripts in ordinary words."
        )
    else:
        brief = (
            "Write this chapter as part of ONE book, not a standalone essay. "
            "Teach ONLY this chapter title — one idea. "
            "Assume prior syllabus chapters were read; do not re-teach them. "
            "Open given→new: first sentences use what the prior chapter taught, "
            "then one new move. "
            "Beginner-friendly literary prose, one calm stream: "
            "picture, worked example, then the name; traps as sentences. "
            "Preserve the article's conceptual spine: definitions, contrasts, "
            "and real examples from the excerpt must survive into the chapter. "
            "If the excerpt is thin, fill pedagogical gaps without inventing APIs. "
            "For foundation/architecture/flow chapters, include one ```mermaid diagram. "
            "For a two-sided contrast, prefer a markdown table. "
            "No blockquote callouts; headings are assertions, not Введение/Ловушка. "
            "Plain markdown code fences (no HTML / highlighter tokens). "
            "Fence tags must match the body: Python → ```python, SQL → ```sql, "
            "diagrams → ```mermaid. Never label application code as sql. "
            "Never include homework, lab assignments, numbered tasks for the learner, "
            "MCQ quizzes, 'Проверьте себя', or answer keys. "
            "If quizzes/practice are ON they own those; if OFF, do not invent them here either. "
            "When Source figures are listed, embed at most 1–2 as exact markdown images "
            "if they clarify this chapter; never invent image URLs. "
            "Reuse book_spine voice/throughline/glossary; open with bridge_from_prev when present. "
            "Write in the course locale, not the excerpt language."
        )
    if not is_first:
        return brief
    return (
        "Chapter 1 is the epitome: open with one miniature complete working story "
        "(scene, tiny program, case, or utterance) the learner could finish after "
        "this chapter alone — then name the pieces. Forbidden: glossary-only open, "
        "'what you will learn', term dump.\n" + brief
    )


def _book_spine_block(spine: dict[str, str]) -> str:
    return "\n".join(
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


def _prompt_section(heading: str, content: str) -> str:
    return f"## {heading}\n{content}" if content else ""


def _source_figures_section(source_images: str) -> str:
    if not source_images:
        return ""
    return (
        "## Source figures (optional)\n"
        "Embed at most 1–2 lines EXACTLY as given only when they illustrate THIS chapter. "
        "If none apply, omit images entirely — do not reuse figures from other chapters. "
        "Do not invent URLs.\n"
        f"{source_images}"
    )


def _join_prompt_parts(parts: list[str]) -> str:
    return "\n\n".join(part for part in parts if part)


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
    prior_chapter_digest: str = "",
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
    writing_brief = _theory_writing_brief(compact=compact, is_first=index == 0)
    spine_block = _book_spine_block(spine)
    excerpt = chapter.get("source_excerpt") or ""
    if compact and len(excerpt) > 4_200:
        excerpt = excerpt[:4_200].rstrip() + "…"
    shown_title = chapter_title or chapter["title"]
    return _join_prompt_parts(
        [
            "## Stage\ntheory_chapter",
            locale_prompt_block(body.locale),
            f"## Audience\n{audience}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            _prompt_section("Book spine", spine_block),
            f"## Full syllabus ({len(chapters)} chapters)\n{syllabus}",
            f"## This chapter\n{index + 1}/{len(chapters)}: {shown_title}",
            f"## Previous chapter\n{prev_title}",
            f"## Next chapter\n{next_title}",
            _prompt_section("Prior chapters digest", prior_chapter_digest),
            _prompt_section("Bridge from previous", bridge),
            _prompt_section("Assumes known", assumes),
            _prompt_section("Must not reteach", must_not),
            _prompt_section("Chapter purpose", purpose),
            _prompt_section("Learning objective", learning_objective),
            _prompt_section("Source titles for this chapter", source_titles),
            f"## Chapter id\n{chapter['id']}",
            f"## Source excerpt\n<source_excerpt>\n{excerpt}\n</source_excerpt>",
            _source_figures_section(source_images),
            f"## Writing brief\n{writing_brief}",
            output,
        ]
    )
