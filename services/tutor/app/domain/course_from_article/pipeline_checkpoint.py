from __future__ import annotations

import uuid
from typing import Any

from app.config import TutorConfig
from app.domain.course_build import CourseBuildMeta, CourseBuildStore
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.studio_schemas import CourseFromArticleRequest


def builds_store(config: TutorConfig) -> CourseBuildStore:
    return CourseBuildStore(config.course_builds_root, ttl_days=config.course_build_ttl_days)


def resolve_build_session(
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
) -> tuple[CourseBuildStore, CourseBuildMeta, CourseFromArticleRequest, bool]:
    """Return store, meta, effective request, and whether this is a resume."""
    store = builds_store(config)
    mode = "topic_bundles" if body.uses_topic_bundles() else "legacy"
    if body.build_id is None:
        request_payload = body.model_dump(mode="json", exclude={"build_id"})
        title = (body.title or "").strip() or "Course draft"
        meta = store.create(
            user_id=user_id,
            request_payload=request_payload,
            title=title,
            mode=mode,
        )
        return store, meta, body.model_copy(update={"build_id": uuid.UUID(meta.build_id)}), False

    build_id = body.build_id
    try:
        meta = store.load_meta(user_id, build_id)
    except FileNotFoundError as exc:
        raise TutorError(status.HTTP_404_NOT_FOUND, "course build not found") from exc
    except PermissionError as exc:
        raise TutorError(status.HTTP_403_FORBIDDEN, "course build forbidden") from exc

    if meta.status == "done":
        raise TutorError(status.HTTP_409_CONFLICT, "course build already completed")

    saved = store.load_request(user_id, build_id)
    saved.pop("build_id", None)
    restored = CourseFromArticleRequest.model_validate({**saved, "build_id": str(build_id)})
    # Gates from the current call override saved ones — and persist for next resume.
    dirty = False
    if body.ignore_deviations and not restored.ignore_deviations:
        restored = restored.model_copy(update={"ignore_deviations": True})
        dirty = True
    if body.code_suitability_action is not None:
        restored = restored.model_copy(
            update={"code_suitability_action": body.code_suitability_action}
        )
        dirty = True
    if dirty:
        store.save_request(
            user_id,
            build_id,
            restored.model_dump(mode="json", exclude={"build_id"}),
        )
    store.patch_meta(
        user_id,
        build_id,
        status="running",
        message="Resuming course build",
        clear_error=True,
    )
    meta = store.load_meta(user_id, build_id)
    return store, meta, restored, True


def emit_build_event(meta: CourseBuildMeta) -> dict[str, object]:
    return {
        "type": "stage",
        "stage": meta.stage,
        "status": "running",
        "progress": meta.progress,
        "message": meta.message or "Course build checkpoint",
        "message_key": "buildCheckpoint",
        "detail": {
            "build_id": meta.build_id,
            "chapters_done": meta.chapters_done,
            "chapter_total": meta.chapter_total,
            "build_status": meta.status,
        },
    }


def sync_progress_from_event(
    store: CourseBuildStore,
    *,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    event: dict[str, object],
) -> None:
    stage = str(event.get("stage") or "")
    progress = event.get("progress")
    message = event.get("message")
    kwargs: dict[str, Any] = {}
    if stage and stage not in {"failed", "done"}:
        kwargs["stage"] = stage
    if isinstance(progress, int | float):
        kwargs["progress"] = float(progress)
    if isinstance(message, str) and message.strip():
        kwargs["message"] = message.strip()[:500]
    if kwargs:
        store.patch_meta(user_id, build_id, **kwargs)


def mark_build_paused(
    store: CourseBuildStore,
    *,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    message: str,
    failed: bool = False,
) -> None:
    store.patch_meta(
        user_id,
        build_id,
        status="failed" if failed else "paused",
        message=message[:500],
        error=message[:500],
    )


def mark_build_done(
    store: CourseBuildStore,
    *,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
) -> None:
    store.patch_meta(
        user_id,
        build_id,
        status="done",
        stage="done",
        progress=1.0,
        message="Course generation complete",
        clear_error=True,
    )
