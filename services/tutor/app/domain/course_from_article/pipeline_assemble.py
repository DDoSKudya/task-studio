from __future__ import annotations

from collections.abc import AsyncIterator

from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.pack import collect_manifest_errors
from studio_contracts.studio_schemas import CourseDeviation, CourseFromArticleMeta

from .assemble import _assemble_manifest, _repair_manifest_shapes
from .progress import _stage_event


async def iter_assemble_stage(
    *,
    pack_id: str,
    title: str,
    locale: str,
    runtime: str,
    runtime_version: str,
    theory_steps: list[dict[str, object]],
    video_steps: list[dict[str, object]],
    quiz_steps: list[dict[str, object]],
    code_steps: list[dict[str, object]],
    chapters: list[dict[str, str]],
    outcomes: list[str],
    warnings: list[str],
    deviations: list[CourseDeviation],
    sources_count: int,
    band_assemble: tuple[float, float],
) -> AsyncIterator[dict[str, object]]:
    if not theory_steps and not quiz_steps and not code_steps and not video_steps:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course generation produced no content steps")

    yield _stage_event(
        stage="assemble",
        status="running",
        progress=band_assemble[0],
        message="Assembling and validating pack manifest",
        message_key="assembleRunning",
    )
    manifest = _assemble_manifest(
        pack_id=pack_id,
        title=title,
        locale=locale,
        runtime=runtime,
        runtime_version=runtime_version,
        theory_steps=theory_steps,
        video_steps=video_steps,
        quiz_steps=quiz_steps,
        code_steps=code_steps,
    )
    issues = collect_manifest_errors(manifest)
    if issues:
        warnings.append(
            "manifest validation: " + "; ".join(f"{i.path}: {i.message}" for i in issues[:5])
        )
        manifest = _repair_manifest_shapes(manifest)
        issues = collect_manifest_errors(manifest)
    if issues:
        raise TutorError(
            status.HTTP_502_BAD_GATEWAY,
            "generated manifest invalid: "
            + "; ".join(f"{i.path}: {i.message}" for i in issues[:8]),
        )

    chapter_titles = [str(step.get("title") or step.get("id")) for step in theory_steps] or [
        str(chapter.get("title") or chapter.get("id")) for chapter in chapters
    ]
    meta = CourseFromArticleMeta(
        outcomes=outcomes,
        warnings=warnings,
        chapters=chapter_titles,
        deviations=deviations,
        article_count=sources_count,
    )
    yield _stage_event(
        stage="assemble",
        status="done",
        progress=band_assemble[1],
        message="Course pack ready",
        message_key="assembleDone",
        detail={
            "pack_id": pack_id,
            "title": title,
            "theory_steps": len(theory_steps),
            "video_steps": len(video_steps),
            "quiz_steps": len(quiz_steps),
            "code_steps": len(code_steps),
            "warnings": warnings,
            "article_count": sources_count,
        },
    )
    yield {
        "type": "done",
        "stage": "done",
        "status": "done",
        "progress": 1.0,
        "message": "Course generation complete",
        "message_key": "generationComplete",
        "manifest": manifest,
        "meta": meta.model_dump(mode="json"),
    }
