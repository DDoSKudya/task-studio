from __future__ import annotations

import json

from studio_contracts.studio_schemas import CourseFromArticleRequest

from .constants import _MAX_CHAPTERS


def _analyze_user_message(
    body: CourseFromArticleRequest,
    article: str,
    *,
    sources: list[dict[str, object]] | None = None,
) -> str:
    source_rows = sources or []
    multi = len(source_rows) > 1
    source_catalog = "\n".join(
        f"- Source {index}: {item['title']} ({len(str(item['content']))} chars)"
        for index, item in enumerate(source_rows, start=1)
    )
    process = (
        "1) Inventory concepts from EVERY source.\n"
        "2) Deduplicate overlaps into shared course topics.\n"
        "3) Order by learning dependency: foundations → core → depth → traps.\n"
        "4) Name chapters for the course (not for a single article file).\n"
        "5) Attach verbatim source_excerpt + source_titles per chapter.\n"
        "6) Emit book_spine (voice, address, throughline, glossary, metaphors) "
        "so theory chapters read as one book.\n"
        "7) Per chapter: bridge_from_prev, assumes_known, must_not_reteach."
    )
    constraints = [
        f"Max {_MAX_CHAPTERS} chapters.",
        "One idea per chapter.",
        "Course title must describe the whole subject, not only the deepest subtopic.",
        "The syllabus must feel like one authored book, not a stack of article dumps.",
    ]
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
            f"## Locale\n{body.locale}",
            (
                "## Audience\n"
                + (body.audience or "beginners and intermediate developers who need mental models")
            ),
            f"## Preferred title\n{body.title or '(derive a course-level title from all sources)'}",
            f"## Sources catalog\n{source_catalog or '- (single corpus below)'}",
            "## Constraints\n" + "\n".join(f"- {item}" for item in constraints),
            f"## Process\n{process}",
            f"## Source corpus\n<source_corpus>\n{article}\n</source_corpus>",
            "## Output\nJSON skeleton only: pack_id, title, locale, audience_level, domain, "
            "outcomes, book_spine, chapters[{id,title}]. "
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
    return "\n\n".join(
        part
        for part in [
            "## Stage\nanalyze",
            "## Role\nFill details for ONE syllabus chapter only.",
            f"## Locale\n{body.locale}",
            f"## Chapter position\n{index + 1}/{total}",
            f"## Chapter id\n{chapter.get('id') or ''}",
            f"## Chapter title\n{chapter.get('title') or ''}",
            f"## Outcomes\n{json.dumps(outcomes, ensure_ascii=False)}",
            f"## Sources catalog\n{source_catalog or '- (corpus below)'}",
            f"## Source corpus\n<source_corpus>\n{article}\n</source_corpus>",
            "## Output\n"
            "ONE JSON object for this chapter only: "
            '{"chapter":{"id","title","purpose","bridge_from_prev","assumes_known",'
            '"must_not_reteach","source_titles","source_excerpt"}} '
            "OR the chapter fields at the top level. "
            "source_excerpt ≤ 500 characters. Do not emit other chapters.",
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
            f"## Locale\n{body.locale}",
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
) -> str:
    chapter_title = title or chapter["title"]
    return _theory_shared_context(
        chapter,
        body,
        outcomes,
        chapters=chapters,
        index=index,
        book_spine=book_spine,
        chapter_title=chapter_title,
        output=(
            "## Output\nPlain markdown for this chapter only. "
            "Write the full teaching content the learner needs — do not truncate on purpose. "
            "If the answer hits a length limit, stop cleanly; a continue pass will follow."
        ),
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
) -> str:
    syllabus = "\n".join(f"{i + 1}. {item['title']}" for i, item in enumerate(chapters))
    prev_title = chapters[index - 1]["title"] if index > 0 else "(course start)"
    next_title = chapters[index + 1]["title"] if index + 1 < len(chapters) else "(course end)"
    purpose = chapter.get("purpose") or ""
    source_titles = chapter.get("source_titles") or ""
    bridge = chapter.get("bridge_from_prev") or ""
    assumes = chapter.get("assumes_known") or ""
    must_not = chapter.get("must_not_reteach") or ""
    spine = book_spine or {}
    audience = body.audience or (
        "beginners: mental models first, then jargon; little prior knowledge of this topic"
    )
    writing_brief = (
        "Write this chapter as part of ONE book, not a standalone essay. "
        "Teach ONLY this chapter title — one idea. "
        "Assume prior syllabus chapters were read; "
        "do not re-teach them. "
        "Beginner-friendly literary prose: "
        "mental model + worked example + traps. "
        "If the excerpt is thin, fill pedagogical gaps without inventing APIs. "
        "For foundation/architecture/flow chapters, include one ```mermaid diagram. "
        "Plain markdown code fences (no HTML / highlighter tokens). "
        "Fence tags must match the body: Python/SQLAlchemy → ```python, raw SQL → ```sql, "
        "diagrams → ```mermaid. "
        "Never label `with Session(...) as session:` as sql. "
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
    shown_title = chapter_title or chapter["title"]
    return "\n\n".join(
        part
        for part in [
            "## Stage\ntheory_chapter",
            f"## Locale\n{body.locale}",
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
            f"## Source titles for this chapter\n{source_titles}" if source_titles else "",
            f"## Chapter id\n{chapter['id']}",
            f"## Source excerpt\n<source_excerpt>\n{chapter['source_excerpt']}\n</source_excerpt>",
            f"## Writing brief\n{writing_brief}",
            output,
        ]
        if part
    )
