from __future__ import annotations

from app.api.deps import ClientDep, ConfigDep, UserId
from app.api.routes.studio_stream import course_stream_response
from app.domain.course_from_article import generate_course_from_article, stream_course_from_article
from app.domain.fetch_article_from_url import fetch_article_from_url
from app.domain.studio import suggest_pack_fragment
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from studio_contracts.studio_schemas import (
    CourseFromArticleRequest,
    CourseFromArticleResponse,
    FetchArticleFromUrlRequest,
    FetchArticleFromUrlResponse,
    StudioSuggestRequest,
    StudioSuggestResponse,
)

router = APIRouter()


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
