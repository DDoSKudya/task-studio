from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from app.domain.course_strategies.code_templates import code_template_is_substantive
from app.domain.course_strategies.gates import (
    chapter_title_is_valid,
    choices_are_letter_only,
    question_embeds_choices,
    quiz_stem_key,
)

_AUTHOR_BIO = re.compile(
    r"(меня зовут|my name is|привет[,!]?\s+меня)",
    re.IGNORECASE,
)
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_MERMAID = re.compile(r"```mermaid", re.IGNORECASE)
_COMPILED_QUIZ_ID = re.compile(r"-quiz-g\d+$")
_QUIZ_SHORTFALL = re.compile(r"\bkept\s+\d+\s+of\s+\d+\s+questions\b", re.IGNORECASE)
_WEAK_PRACTICE_SCORE = re.compile(
    r"practice quality gate weak after reinforce:.*?\bscore~([0-9.]+)",
    re.IGNORECASE,
)


@dataclass(slots=True)
class QualityAudit:
    level: str
    score: int = 100
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    must_fix: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "score": self.score,
            "passed": list(self.passed),
            "failed": list(self.failed),
            "must_fix": list(self.must_fix),
            "notes": list(self.notes),
        }


def audit_course_quality(
    *,
    chapters: Sequence[Mapping[str, object]],
    theory_steps: Sequence[Mapping[str, object]],
    quizzes: Sequence[Mapping[str, object]],
    practices: Sequence[Mapping[str, object]],
    source_has_figures: bool = False,
    phase_order: list[str] | None = None,
    warnings: Sequence[str] = (),
    expects_executable_practice: bool = False,
) -> QualityAudit:

    audit = QualityAudit(level="none")
    titles_ok = all(
        chapter_title_is_valid(str(item.get("title") or "")) for item in chapters
    ) and bool(chapters)
    if titles_ok:
        audit.passed.append("L0.title_gate")
    else:
        audit.failed.append("L0.title_gate")
    if chapters:
        audit.passed.append("L0.has_chapters")
    else:
        audit.failed.append("L0.has_chapters")
    if phase_order:
        audit.passed.append("L0.phase_order")
    if audit.failed:
        audit.level = "none"
        _score_audit(audit, quizzes=quizzes)
        return audit
    audit.level = "L0"

    theory_blob = "\n".join(str(step.get("content") or "") for step in theory_steps)
    bio_dump = bool(_AUTHOR_BIO.search(theory_blob))
    if theory_steps and not bio_dump:
        audit.passed.append("L1.no_author_bio")
        audit.level = "L1"
    elif bio_dump:
        audit.failed.append("L1.no_author_bio")
    else:
        audit.notes.append("L1 skipped: no theory steps")

    has_figure = bool(_MD_IMAGE.search(theory_blob))
    has_mermaid = bool(_MERMAID.search(theory_blob))
    if has_figure or has_mermaid:
        audit.passed.append("L2.visual")
        if audit.level == "L1":
            audit.level = "L2"
    elif source_has_figures:
        audit.failed.append("L2.source_figures_missing_in_theory")
    else:
        audit.failed.append("L2.visual_missing")

    assess_failed = _audit_assess(audit, quizzes=quizzes, practices=practices)
    _audit_generation_warnings(
        audit,
        warnings,
        expects_executable_practice=expects_executable_practice,
    )
    if quizzes and not assess_failed and not audit.failed and audit.level in {"L1", "L2"}:
        audit.level = "L3"
    _score_audit(audit, quizzes=quizzes)
    return audit


def _audit_generation_warnings(
    audit: QualityAudit,
    warnings: Sequence[str],
    *,
    expects_executable_practice: bool,
) -> None:
    folded = [warning.casefold() for warning in warnings]
    if any(_QUIZ_SHORTFALL.search(warning) for warning in warnings):
        audit.failed.append("L3.quiz_count_shortfall")
    if any("compiled from chapter theory" in warning for warning in folded):
        audit.failed.append("L3.compiled_quiz_fallback")
    if any(
        "practice converted to open task after weak code template" in warning for warning in folded
    ):
        audit.failed.append("L3.practice_template_tiny")
    weak_scores = [
        float(match.group(1))
        for warning in warnings
        if (match := _WEAK_PRACTICE_SCORE.search(warning)) is not None
    ]
    if any(score < 0.7 for score in weak_scores):
        audit.failed.append("L3.practice_quality_low")
    if expects_executable_practice and any(
        "open tasks (not a code editor)" in warning for warning in folded
    ):
        audit.failed.append("L3.open_practice_for_tool_course")


def _score_audit(
    audit: QualityAudit,
    *,
    quizzes: Sequence[Mapping[str, object]],
) -> None:
    compiled = sum(
        1
        for quiz in quizzes
        if str(quiz.get("generation") or "") == "compiled"
        or _COMPILED_QUIZ_ID.search(str(quiz.get("id") or "")) is not None
    )
    if compiled and "L3.compiled_quiz_fallback" not in audit.failed:
        audit.failed.append("L3.compiled_quiz_fallback")
    penalties = {
        "L0.title_gate": 35,
        "L0.has_chapters": 50,
        "L2.source_figures_missing_in_theory": 15,
        "L2.visual_missing": 10,
        "L3.quiz_count_shortfall": 25,
        "L3.compiled_quiz_fallback": 20,
        "L3.open_practice_for_tool_course": 20,
        "L3.practice_not_runnable": 20,
        "L3.practice_template_tiny": 25,
        "L3.practice_quality_low": 20,
    }
    audit.must_fix = list(dict.fromkeys(audit.failed))
    base_penalty = sum(penalties.get(failure, 8) for failure in audit.must_fix)
    compiled_share_penalty = round(20 * compiled / len(quizzes)) if quizzes else 0
    audit.score = max(0, 100 - base_penalty - compiled_share_penalty)


def _audit_assess(
    audit: QualityAudit,
    *,
    quizzes: Sequence[Mapping[str, object]],
    practices: Sequence[Mapping[str, object]],
) -> bool:
    before = len(audit.failed)
    items = [item for item in quizzes if isinstance(item, dict)]
    if any(choices_are_letter_only(item.get("choices")) for item in items):
        audit.failed.append("L3.letter_only_choices")
    elif items:
        audit.passed.append("L3.no_letter_only_choices")

    if any(
        question_embeds_choices(str(item.get("question") or ""), item.get("choices"))
        for item in items
    ):
        audit.failed.append("L3.choices_inside_question")

    stems = [quiz_stem_key(str(item.get("question") or "")) for item in items]
    filled = [stem for stem in stems if stem]
    if len(filled) != len(set(filled)):
        audit.failed.append("L3.duplicate_quiz_stems")

    _audit_practices(audit, practices)
    return len(audit.failed) > before


def _audit_practices(
    audit: QualityAudit,
    practices: Sequence[Mapping[str, object]],
) -> None:
    if not practices:
        return
    runnable = [
        item
        for item in practices
        if str(item.get("checker") or "") != "llm"
        or (isinstance(item.get("tests"), list) and item.get("tests"))
    ]
    if runnable:
        audit.passed.append("L3.practice_runtime")
    else:
        audit.failed.append("L3.practice_not_runnable")
    if any(not str(item.get("runtime") or "").strip() for item in practices):
        audit.failed.append("L3.practice_runtime_missing")
    if any("```" in str(item.get("template") or "") for item in practices):
        audit.failed.append("L3.practice_template_markdown")
    code_practices = [
        item for item in practices if str(item.get("kind") or "") == "code" or "template" in item
    ]
    if any(
        not code_template_is_substantive(str(item.get("template") or "")) for item in code_practices
    ):
        audit.failed.append("L3.practice_template_tiny")
