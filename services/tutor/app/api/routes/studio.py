from __future__ import annotations

import uuid

from app.api.deps import ClientDep, ConfigDep, UserId
from app.api.routes.studio_stream import course_stream_response
from app.domain.authoring.studio import suggest_pack_fragment
from app.domain.course_build import CourseBuildMeta, CourseBuildStore
from app.domain.course_from_article import generate_course_from_article, stream_course_from_article
from app.domain.errors import TutorError
from app.domain.fetch_article_from_url import fetch_article_from_url
from app.domain.fetch_article_from_url.sources.service import fetch_articles_from_urls
from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from studio_contracts.api.studio_schemas import (
    CourseBuildDetail,
    CourseBuildStatus,
    CourseBuildSummary,
    CourseFromArticleRequest,
    CourseFromArticleResponse,
    FetchArticleFromUrlRequest,
    FetchArticleFromUrlResponse,
    FetchArticlesFromUrlsRequest,
    FetchArticlesFromUrlsResponse,
    StudioSuggestRequest,
    StudioSuggestResponse,
)

router = APIRouter()


def _store(config: ConfigDep) -> CourseBuildStore:
    return CourseBuildStore(config.course_builds_root, ttl_days=config.course_build_ttl_days)


def _summary_from_meta(meta: CourseBuildMeta) -> CourseBuildSummary:
    status_value: CourseBuildStatus
    if meta.status == "running":
        status_value = "running"
    elif meta.status == "failed":
        status_value = "failed"
    elif meta.status == "done":
        status_value = "done"
    else:
        status_value = "paused"
    return CourseBuildSummary(
        build_id=uuid.UUID(meta.build_id),
        title=meta.title,
        status=status_value,
        stage=meta.stage,
        progress=min(1.0, max(0.0, meta.progress)),
        message=meta.message,
        chapter_total=meta.chapter_total,
        chapters_done=meta.chapters_done,
        error=meta.error,
        created_at=meta.created_at,
        updated_at=meta.updated_at,
        mode=meta.mode,
    )


def _detail_from_meta(
    meta: CourseBuildMeta,
    request_payload: dict[str, object],
) -> CourseBuildDetail:
    summary = _summary_from_meta(meta)
    return CourseBuildDetail(**summary.model_dump(mode="python"), request=request_payload)


@router.get("/studio/course-builds", response_model=list[CourseBuildSummary])
async def list_course_builds(user_id: UserId, config: ConfigDep) -> list[CourseBuildSummary]:
    items = _store(config).list_for_user(user_id, include_done=True)
    return [_summary_from_meta(item) for item in items]


@router.get("/studio/course-builds/{build_id}", response_model=CourseBuildDetail)
async def get_course_build(
    build_id: uuid.UUID,
    user_id: UserId,
    config: ConfigDep,
) -> CourseBuildDetail:
    store = _store(config)
    try:
        meta = store.load_meta(user_id, build_id)
        request_payload = store.load_request(user_id, build_id)
    except FileNotFoundError as exc:
        raise TutorError(status.HTTP_404_NOT_FOUND, "course build not found") from exc
    except PermissionError as exc:
        raise TutorError(status.HTTP_403_FORBIDDEN, "course build forbidden") from exc
    except ValueError as exc:
        raise TutorError(status.HTTP_404_NOT_FOUND, "course build not found") from exc
    return _detail_from_meta(meta, request_payload)


@router.delete("/studio/course-builds/{build_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard_course_build(
    build_id: uuid.UUID,
    user_id: UserId,
    config: ConfigDep,
) -> None:
    store = _store(config)
    try:
        store.load_meta(user_id, build_id)
    except FileNotFoundError as exc:
        raise TutorError(status.HTTP_404_NOT_FOUND, "course build not found") from exc
    except PermissionError as exc:
        raise TutorError(status.HTTP_403_FORBIDDEN, "course build forbidden") from exc
    store.discard(user_id, build_id)
    store.prune_expired(user_id)


@router.post("/studio/suggest", response_model=StudioSuggestResponse)
async def studio_suggest(
    body: StudioSuggestRequest,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
) -> StudioSuggestResponse:
    return await suggest_pack_fragment(
        client,
        config,
        user_id=user_id,
        body=body,
    )


@router.post("/studio/fetch-article-from-url", response_model=FetchArticleFromUrlResponse)
async def studio_fetch_article_from_url(
    body: FetchArticleFromUrlRequest,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
) -> FetchArticleFromUrlResponse:
    return await fetch_article_from_url(
        client,
        config,
        user_id=user_id,
        body=body,
    )


@router.post("/studio/fetch-articles-from-urls", response_model=FetchArticlesFromUrlsResponse)
async def studio_fetch_articles_from_urls(
    body: FetchArticlesFromUrlsRequest,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
) -> FetchArticlesFromUrlsResponse:
    return await fetch_articles_from_urls(
        client,
        config,
        user_id=user_id,
        body=body,
    )


@router.post("/studio/course-from-article", response_model=CourseFromArticleResponse)
async def studio_course_from_article(
    body: CourseFromArticleRequest,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
) -> CourseFromArticleResponse:
    return await generate_course_from_article(
        client,
        config,
        user_id=user_id,
        body=body,
    )


@router.post("/studio/course-from-article/stream")
async def studio_course_from_article_stream(
    body: CourseFromArticleRequest,
    user_id: UserId,
    config: ConfigDep,
    client: ClientDep,
) -> StreamingResponse:
    return course_stream_response(
        stream_course_from_article(
            client,
            config,
            user_id=user_id,
            body=body,
        )
    )
