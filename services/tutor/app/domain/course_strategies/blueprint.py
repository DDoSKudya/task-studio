from __future__ import annotations

import re
from typing import TypedDict

from app.domain.course_strategies.document_blocks import DocumentBlock, parse_document_blocks
from app.domain.course_strategies.gates import sanitize_chapter_title

_TOKEN = re.compile(r"[A-Za-zА-Яа-я0-9_]{4,}")
_APIISH = re.compile(
    r"(?:/[A-Za-z0-9_\-{}]+)|(?:\b[A-Z][A-Za-z0-9_]{2,}\b)|(?:\b[a-z]+_[a-z0-9_]+\b)"
)
_FLOW_TITLE_MARKERS = (
    "архитектур",
    "architecture",
    "как устроен",
    "как работает",
    "как начать",
    "flow",
    "pipeline",
    "процесс",
    "process",
    "этап",
    "stage",
    "последовательн",
    "sequence",
    "взаимодейств",
    "interaction",
    "переход",
    "transition",
    "цикл",
    "cycle",
    "жизненн",
    "lifecycle",
    "против",
    "versus",
    " vs ",
    "сравнен",
    "compar",
    "структур",
    "structure",
)


class VisualPlan(TypedDict):
    type: str
    note: str


class FigureRef(TypedDict):
    url: str
    alt: str


class ChapterBlueprint(TypedDict):
    chapter_id: str
    title: str
    objective: str
    key_claims: list[str]
    source_block_ids: list[str]
    required_figures: list[FigureRef]
    visual_plan: VisualPlan


def _claims_from_text(text: str, *, limit: int = 4) -> list[str]:
    sentences = re.split(r"(?<=[.!?…])\s+", " ".join((text or "").split()))
    claims: list[str] = []
    for sentence in sentences:
        cleaned = sentence.strip()
        if len(cleaned) < 28:
            continue
        if _APIISH.search(cleaned) or len(cleaned.split()) >= 8:
            claims.append(cleaned[:220])
        if len(claims) >= limit:
            break
    if not claims and text.strip():
        claims.append(" ".join(text.split())[:220])
    return claims


def _overlap_score(excerpt: str, block: DocumentBlock) -> float:
    left = {token.casefold() for token in _TOKEN.findall(excerpt)}
    right = {token.casefold() for token in _TOKEN.findall(block.text)}
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, min(len(left), len(right)))


def _visual_plan_for(
    blocks: list[DocumentBlock],
    *,
    has_figure: bool,
    title: str = "",
) -> VisualPlan:
    if has_figure:
        return {"type": "source_figure", "note": "use required_figures"}
    if any(block.kind == "table" for block in blocks):
        return {"type": "table", "note": "compare table from source"}
    title_fold = (title or "").casefold()
    wants_flow = any(marker in title_fold for marker in _FLOW_TITLE_MARKERS)
    if wants_flow or any(block.kind == "code" for block in blocks):
        return {"type": "mermaid", "note": "architecture or flow from code/claims"}
    return {"type": "none", "note": ""}


def build_chapter_blueprint(
    chapter: dict[str, str],
    *,
    all_blocks: list[DocumentBlock] | None = None,
) -> ChapterBlueprint:
    excerpt = str(chapter.get("source_excerpt") or "")
    title = sanitize_chapter_title(
        str(chapter.get("title") or ""),
        fallback=str(chapter.get("id") or "Topic"),
    )
    local_blocks = parse_document_blocks(excerpt, source_prefix=str(chapter.get("id") or "ch"))
    matched: list[DocumentBlock] = list(local_blocks)
    if all_blocks and not matched:
        ranked = sorted(
            all_blocks,
            key=lambda block: _overlap_score(excerpt or title, block),
            reverse=True,
        )
        matched = [block for block in ranked[:8] if _overlap_score(excerpt or title, block) >= 0.15]
    figures: list[FigureRef] = [
        {"url": block.url, "alt": block.alt or "figure"}
        for block in matched
        if block.kind == "figure" and block.url
    ]
    source_images = str(chapter.get("source_images") or "")
    for match in re.finditer(r"!\[([^\]]*)\]\(([^)\s]+)\)", source_images):
        url = match.group(2).strip()
        if url and not any(item["url"] == url for item in figures):
            figures.append({"url": url, "alt": match.group(1).strip() or "figure"})
    claims = _claims_from_text(excerpt)
    return {
        "chapter_id": str(chapter.get("id") or ""),
        "title": title,
        "objective": str(chapter.get("objective") or title)[:400],
        "key_claims": claims,
        "source_block_ids": [block.block_id for block in matched[:12]],
        "required_figures": figures[:3],
        "visual_plan": _visual_plan_for(matched, has_figure=bool(figures), title=title),
    }


def build_course_blueprints(
    chapters: list[dict[str, str]],
    *,
    source_blocks: list[DocumentBlock] | None = None,
) -> list[ChapterBlueprint]:
    return [build_chapter_blueprint(chapter, all_blocks=source_blocks) for chapter in chapters]
