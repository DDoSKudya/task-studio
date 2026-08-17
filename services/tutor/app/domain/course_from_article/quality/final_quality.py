from __future__ import annotations

import re
import uuid

from app.domain.course_build import CourseBuildStore
from app.domain.course_from_article.local_course.curriculum.collapse import is_shell_title
from app.domain.course_from_article.pack.assemble_manifest import _topic_keys
from app.domain.course_from_article.practice.practice_routing import is_command_oriented_course
from app.domain.course_strategies import (
    audit_course_quality,
    blocks_from_sources,
    build_course_blueprints,
    chapter_title_is_valid,
    dedupe_quiz_batch,
    ensure_mermaid_from_visual_plan,
)
from app.domain.course_strategies.blueprint import ChapterBlueprint
from app.domain.llm.content.prose_dedupe import clean_theory_markdown

_HEADING_ONLY = re.compile(r"^#{1,3}\s+\S.*$")


def _filter_steps_for_chapters(
    steps: list[dict[str, object]],
    *,
    known_ids: set[str],
    kept_ids: set[str],
) -> None:
    steps[:] = [
        step
        for step in steps
        if not (
            (chapter_id := str(step.get("chapter_id") or "").strip())
            and chapter_id in known_ids
            and chapter_id not in kept_ids
        )
    ]


def _apply_chapter_gate(
    chapters: list[dict[str, str]],
    *,
    theory_steps: list[dict[str, object]],
    quizzes: list[dict[str, object]],
    practices: list[dict[str, object]],
    warnings: list[str],
) -> None:
    topic_keys = _topic_keys(chapters)
    accepted_indexes = [
        index
        for index, chapter in enumerate(chapters)
        if chapter_title_is_valid(chapter.get("title") or "")
        and not is_shell_title(chapter.get("title") or "")
    ]
    if not accepted_indexes or len(accepted_indexes) == len(chapters):
        if chapters and not accepted_indexes:
            warnings.append(
                "final quality: title gate rejected every chapter; kept original outline"
            )
        return

    known_ids = set(topic_keys)
    known_ids.update(str(chapter.get("id") or "").strip() for chapter in chapters)
    kept_ids = {topic_keys[index] for index in accepted_indexes}
    kept_ids.update(str(chapters[index].get("id") or "").strip() for index in accepted_indexes)
    chapters[:] = [chapters[index] for index in accepted_indexes]
    for steps in (theory_steps, quizzes, practices):
        _filter_steps_for_chapters(steps, known_ids=known_ids, kept_ids=kept_ids)
    warnings.append(
        f"final quality: dropped {len(topic_keys) - len(accepted_indexes)} shell/invalid chapter(s)"
    )


def _clean_theory_steps(
    theory_steps: list[dict[str, object]],
    *,
    warnings: list[str],
) -> None:
    cleaned_theory = 0
    for step in theory_steps:
        content = str(step.get("content") or "")
        cleaned = clean_theory_markdown(content)
        if cleaned and cleaned != content:
            step["content"] = cleaned
            cleaned_theory += 1
    if cleaned_theory:
        warnings.append(f"final quality: cleaned {cleaned_theory} theory chapter(s)")

    kept_theory: list[dict[str, object]] = []
    dropped_thin = 0
    for step in theory_steps:
        if str(step.get("kind") or "theory") != "theory":
            kept_theory.append(step)
            continue
        content = str(step.get("content") or "")
        prose = "\n".join(
            line for line in content.splitlines() if not _HEADING_ONLY.match(line.strip())
        ).strip()
        if len(prose) < 80:
            dropped_thin += 1
            continue
        kept_theory.append(step)
    if dropped_thin and kept_theory:
        theory_steps[:] = kept_theory
        warnings.append(f"final quality: dropped {dropped_thin} heading-only theory step(s)")


def _restore_theory_visuals(
    theory_steps: list[dict[str, object]],
    *,
    blueprints: list[ChapterBlueprint],
) -> int:
    by_chapter = {str(item.get("chapter_id") or ""): item for item in blueprints}
    by_title = {
        " ".join(str(item.get("title") or "").split()).casefold(): item
        for item in blueprints
        if str(item.get("title") or "").strip()
    }
    restored = 0
    for step in theory_steps:
        if str(step.get("kind") or "theory") != "theory":
            continue
        blueprint = by_chapter.get(str(step.get("chapter_id") or "").strip())
        if blueprint is None:
            title_key = " ".join(str(step.get("title") or "").split()).casefold()
            blueprint = by_title.get(title_key)
        if blueprint is None:
            continue
        raw_claims = blueprint.get("key_claims")
        plan = blueprint.get("visual_plan")
        visual_plan = (
            {str(key): value for key, value in plan.items()} if isinstance(plan, dict) else None
        )
        before = str(step.get("content") or "")
        after = ensure_mermaid_from_visual_plan(
            before,
            visual_plan=visual_plan,
            title=str(step.get("title") or blueprint.get("title") or ""),
            key_claims=[str(item) for item in raw_claims] if isinstance(raw_claims, list) else None,
            locale="ru",
        )
        if after != before:
            step["content"] = after
            restored += 1
    return restored


def apply_final_course_quality(
    *,
    chapters: list[dict[str, str]],
    theory_steps: list[dict[str, object]],
    quizzes: list[dict[str, object]],
    practices: list[dict[str, object]],
    sources: list[dict[str, object]],
    strategy_pack: str,
    warnings: list[str],
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
) -> None:
    _apply_chapter_gate(
        chapters,
        theory_steps=theory_steps,
        quizzes=quizzes,
        practices=practices,
        warnings=warnings,
    )

    _clean_theory_steps(theory_steps, warnings=warnings)

    blueprints = build_course_blueprints(
        chapters,
        source_blocks=blocks_from_sources(sources),
    )
    restored_diagrams = _restore_theory_visuals(theory_steps, blueprints=blueprints)
    if restored_diagrams:
        warnings.append(f"final quality: restored {restored_diagrams} mermaid diagram(s)")

    quiz_count = len(quizzes)
    quizzes[:] = dedupe_quiz_batch(quizzes)
    if dropped := quiz_count - len(quizzes):
        warnings.append(f"final quality: dropped {dropped} near-duplicate quiz(es)")

    source_has_figures = any("![" in str(source.get("content") or "") for source in sources)
    source_corpus = "\n".join(str(source.get("content") or "") for source in sources)
    course_title = " ".join(str(chapter.get("title") or "") for chapter in chapters)
    audit = audit_course_quality(
        chapters=chapters,
        theory_steps=theory_steps,
        quizzes=quizzes,
        practices=practices,
        source_has_figures=source_has_figures,
        phase_order=["study", "assess", "practice"],
        warnings=warnings,
        expects_executable_practice=is_command_oriented_course(
            title=course_title,
            corpus=source_corpus,
        ),
    )
    store.save_blueprint(
        user_id,
        build_id,
        {
            "strategy_pack": strategy_pack,
            "chapters": blueprints,
            "quality_audit": audit.to_dict(),
        },
    )
    warnings.append(
        f"strategy_pack={strategy_pack} quality_level={audit.level} "
        f"passed={len(audit.passed)} failed={len(audit.failed)}"
    )
