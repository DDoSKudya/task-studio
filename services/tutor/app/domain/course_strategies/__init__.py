from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.domain.prompt_compose.core import load_prompt

from .audit import QualityAudit, audit_course_quality
from .blueprint import build_chapter_blueprint, build_course_blueprints
from .document_blocks import DocumentBlock, blocks_from_sources, parse_document_blocks
from .gates import (
    chapter_title_is_valid,
    choice_is_placeholder,
    choices_are_letter_only,
    dedupe_quiz_batch,
    question_embeds_choices,
    quiz_stem_key,
    quiz_stems_overlap,
    quizzes_are_near_duplicates,
    sanitize_chapter_title,
    stem_wants_many_answers,
    strip_inline_choice_letters,
    title_is_sentence_fragment,
)
from .montage import (
    ensure_figures_in_theory,
    ensure_mermaid_from_visual_plan,
    montage_theory_from_excerpt,
)
from .policy import resolve_strategy_pack_id
from .practice_runtime import detect_practice_runtime, practice_template_looks_fake

_STRATEGY_LINE = re.compile(
    r"^-\s*(curriculum|theory|quiz|practice|edit|visual):\s*`([^`]+)`",
    re.MULTILINE,
)
_SKILL_ITEM = re.compile(r"`([a-z0-9-]+)`")
_BRIEF_HEADER = re.compile(r"^##\s+LLM brief\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True, slots=True)
class StrategyPack:
    pack_id: str
    strategy_paths: tuple[str, ...]
    skills_compose: tuple[str, ...]
    skills_skip: tuple[str, ...]
    llm_brief: str
    target_level: str


def load_strategy(name: str) -> str:

    return load_prompt(f"strategies/{name}")


def _section_body(text: str, header: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(header)}\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_header = re.search(r"^##\s+\S", text[start:], re.MULTILINE)
    end = start + next_header.start() if next_header else len(text)
    return text[start:end].strip()


def _skills_from_section(body: str) -> tuple[str, ...]:
    if not body or body.casefold().startswith("none"):
        return ()
    found = _SKILL_ITEM.findall(body)
    seen: set[str] = set()
    ordered: list[str] = []
    for name in found:
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return tuple(ordered)


def parse_strategy_pack(pack_id: str) -> StrategyPack:
    raw = load_strategy(f"packs/{pack_id}")
    if not raw:
        return StrategyPack(
            pack_id=pack_id,
            strategy_paths=(),
            skills_compose=(),
            skills_skip=(),
            llm_brief="",
            target_level="",
        )
    paths = tuple(path for _, path in _STRATEGY_LINE.findall(raw))
    compose = _skills_from_section(_section_body(raw, "Skills to compose"))
    skip = _skills_from_section(_section_body(raw, "Skills to skip"))
    brief_match = _BRIEF_HEADER.search(raw)
    brief = ""
    if brief_match:
        brief = raw[brief_match.end() :].strip()
        next_h = re.search(r"^##\s+\S", brief, re.MULTILINE)
        if next_h:
            brief = brief[: next_h.start()].strip()
    target = ""
    target_body = _section_body(raw, "Target quality")
    if target_body:
        target = " ".join(target_body.split())[:120]
    return StrategyPack(
        pack_id=pack_id,
        strategy_paths=paths,
        skills_compose=compose,
        skills_skip=skip,
        llm_brief=brief,
        target_level=target,
    )


def strategy_briefs(pack: StrategyPack) -> str:
    parts: list[str] = []
    if pack.llm_brief:
        parts.append(f"## Active strategy pack\n{pack.pack_id}\n\n{pack.llm_brief}")
    for path in pack.strategy_paths:
        text = load_strategy(path)
        if not text:
            continue
        brief_match = _BRIEF_HEADER.search(text)
        if not brief_match:
            continue
        brief = text[brief_match.end() :].strip()
        next_h = re.search(r"^##\s+\S", brief, re.MULTILINE)
        if next_h:
            brief = brief[: next_h.start()].strip()
        if brief and brief.casefold() != "(empty — no course generation)":
            if brief.startswith("(empty"):
                continue
            parts.append(f"## Strategy `{path}`\n{brief}")
    return "\n\n".join(parts)


def filter_skills_for_pack(
    skill_names: list[str],
    pack: StrategyPack,
) -> list[str]:

    if pack.pack_id == "blocked":
        return []
    skip = set(pack.skills_skip)
    return [name for name in skill_names if name not in skip]


def strategies_root() -> Path:
    return Path(__file__).resolve().parents[2] / "prompts" / "strategies"


__all__ = [
    "DocumentBlock",
    "QualityAudit",
    "StrategyPack",
    "audit_course_quality",
    "blocks_from_sources",
    "build_chapter_blueprint",
    "build_course_blueprints",
    "chapter_title_is_valid",
    "choice_is_placeholder",
    "choices_are_letter_only",
    "dedupe_quiz_batch",
    "detect_practice_runtime",
    "ensure_figures_in_theory",
    "ensure_mermaid_from_visual_plan",
    "filter_skills_for_pack",
    "load_strategy",
    "montage_theory_from_excerpt",
    "parse_document_blocks",
    "parse_strategy_pack",
    "practice_template_looks_fake",
    "question_embeds_choices",
    "quiz_stem_key",
    "quiz_stems_overlap",
    "quizzes_are_near_duplicates",
    "resolve_strategy_pack_id",
    "sanitize_chapter_title",
    "stem_wants_many_answers",
    "strategies_root",
    "strategy_briefs",
    "strip_inline_choice_letters",
    "title_is_sentence_fragment",
]
