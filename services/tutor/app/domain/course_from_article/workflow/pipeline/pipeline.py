from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from app.config import TutorConfig
from app.domain.course_build import CourseBuildStore
from app.domain.course_from_article.workflow.pipeline.pipeline_body import iter_course_pipeline_body
from app.domain.course_from_article.workflow.pipeline.pipeline_checkpoint import (
    mark_build_done,
    mark_build_paused,
    resolve_build_session,
    sync_progress_from_event,
)
from app.domain.errors import TutorError
from fastapi import status
from studio_contracts.api.studio_schemas import (
    CourseFromArticleMeta,
    CourseFromArticleRequest,
    CourseFromArticleResponse,
)

logger = logging.getLogger(__name__)


def _harvest_course_gold(
    config: TutorConfig,
    store: CourseBuildStore,
    *,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
) -> None:
    if not getattr(config, "course_gold_harvest", False):
        return
    raw_root = getattr(config, "course_gold_root", None)
    if raw_root is None or str(raw_root).strip() in {"", "None"}:
        return
    from app.domain.course_adapters.gold import GoldStore, harvest_from_build

    try:
        harvest_from_build(
            store,
            GoldStore(Path(raw_root)),
            user_id=user_id,
            build_id=build_id,
        )
    except (OSError, ValueError, TypeError) as exc:
        logger.warning("course gold harvest skipped: %s", exc)


async def generate_course_from_article(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
) -> CourseFromArticleResponse:
    final: CourseFromArticleResponse | None = None
    async for event in iter_course_from_article(client, config, user_id=user_id, body=body):
        if event.get("type") == "code_suitability_gate":
            raise TutorError(
                status.HTTP_409_CONFLICT,
                "code task suitability requires confirmation "
                "(set code_suitability_action to continue)",
            )
        if event.get("type") == "error":
            code = event.get("status_code")
            status_code = code if isinstance(code, int) else status.HTTP_502_BAD_GATEWAY
            raise TutorError(
                status_code,
                str(event.get("message") or "course generation failed"),
            )
        if event.get("type") == "done":
            manifest = event.get("manifest")
            meta_raw = event.get("meta")
            if not isinstance(manifest, dict):
                raise TutorError(
                    status.HTTP_502_BAD_GATEWAY, "course generation returned no manifest"
                )
            meta = CourseFromArticleMeta.model_validate(meta_raw or {})
            final = CourseFromArticleResponse(manifest=manifest, meta=meta)
    if final is None:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "course generation produced no result")
    return final


async def stream_course_from_article(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
) -> AsyncIterator[bytes]:
    from app.domain.course_from_article.workflow.events.stream_keepalive import (
        iter_course_sse_with_pings,
    )

    async for frame in iter_course_sse_with_pings(
        iter_course_from_article(client, config, user_id=user_id, body=body)
    ):
        yield frame


async def iter_course_from_article(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
) -> AsyncIterator[dict[str, object]]:
    store, build_meta, body, resumed = resolve_build_session(config, user_id=user_id, body=body)
    build_id = uuid.UUID(build_meta.build_id)
    active_model: list[str] = []

    def _pause(message: str, *, failed: bool = False) -> None:
        mark_build_paused(
            store,
            user_id=user_id,
            build_id=build_id,
            message=message,
            failed=failed,
        )

    async def _stop_local_inference() -> None:
        if not config.ollama_url:
            return
        model = (active_model[0] if active_model else "") or config.ollama_model
        if not model:
            return
        from app.domain.ollama.stop import stop_ollama_model

        await stop_ollama_model(client, ollama_url=config.ollama_url, model=model)

    try:
        async for event in _iter_course_from_article_body(
            client,
            config,
            user_id=user_id,
            body=body,
            store=store,
            build_meta=build_meta,
            resumed=resumed,
            active_model=active_model,
        ):
            event_type = event.get("type")
            if event_type in {"stage", "code_suitability_gate"}:
                sync_progress_from_event(store, user_id=user_id, build_id=build_id, event=event)
            if event_type == "code_suitability_gate":
                _pause(str(event.get("message") or "Waiting for confirmation"))
            if event_type == "error":
                _pause(str(event.get("message") or "course generation failed"), failed=True)
            if event_type == "done":
                _harvest_course_gold(config, store, user_id=user_id, build_id=build_id)
                mark_build_done(store, user_id=user_id, build_id=build_id)
                detail = event.setdefault("detail", {})
                if isinstance(detail, dict):
                    detail["build_id"] = str(build_id)
                else:
                    event["detail"] = {"build_id": str(build_id)}
                event["build_id"] = str(build_id)
            yield event
    except asyncio.CancelledError:
        _pause("Cancelled by user", failed=False)
        await _stop_local_inference()
        raise
    except TutorError as exc:
        logger.warning("course pipeline failed: %s", exc.detail)
        _pause(str(exc.detail), failed=exc.status_code >= 500)
        await _stop_local_inference()
        raise
    except Exception as exc:
        _pause(str(exc) or "course generation failed", failed=True)
        await _stop_local_inference()
        raise


async def _iter_course_from_article_body(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: CourseFromArticleRequest,
    store: CourseBuildStore,
    build_meta: object,
    resumed: bool,
    active_model: list[str],
) -> AsyncIterator[dict[str, object]]:
    async for event in iter_course_pipeline_body(
        client,
        config,
        user_id=user_id,
        body=body,
        store=store,
        build_meta=build_meta,  # type: ignore[arg-type]
        resumed=resumed,
        active_model=active_model,
    ):
        yield event
