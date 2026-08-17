from __future__ import annotations

import uuid
from typing import Annotated

from app.api.upstream_stream import COURSE_FROM_ARTICLE_TIMEOUT, stream_response_body
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import parse_upstream, parse_upstream_list, upstream_detail
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from studio_contracts.api.studio_schemas import (
    CourseBuildDetail,
    CourseBuildSummary,
    CourseFromArticleRequest,
    CourseFromArticleResponse,
)

router = APIRouter()

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


@router.get("/ai/course-builds", response_model=list[CourseBuildSummary])
async def list_course_builds(
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> list[CourseBuildSummary]:
    response = await client.get(
        f"{settings.tutor_service_url}/internal/v1/tutor/studio/course-builds",
        headers={"X-User-Id": str(user_id)},
    )
    return parse_upstream_list(response, CourseBuildSummary)


@router.get("/ai/course-builds/{build_id}", response_model=CourseBuildDetail)
async def get_course_build(
    build_id: uuid.UUID,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> CourseBuildDetail:
    response = await client.get(
        f"{settings.tutor_service_url}/internal/v1/tutor/studio/course-builds/{build_id}",
        headers={"X-User-Id": str(user_id)},
    )
    return parse_upstream(response, CourseBuildDetail)


@router.delete("/ai/course-builds/{build_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard_course_build(
    build_id: uuid.UUID,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> Response:
    response = await client.delete(
        f"{settings.tutor_service_url}/internal/v1/tutor/studio/course-builds/{build_id}",
        headers={"X-User-Id": str(user_id)},
    )
    if response.is_error:
        raise HTTPException(status_code=response.status_code, detail=upstream_detail(response))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/ai/course-from-article", response_model=CourseFromArticleResponse)
async def course_from_article(
    body: CourseFromArticleRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> CourseFromArticleResponse:
    response = await client.post(
        f"{settings.tutor_service_url}/internal/v1/tutor/studio/course-from-article",
        headers={"X-User-Id": str(user_id)},
        json=body.model_dump(mode="json"),
        timeout=COURSE_FROM_ARTICLE_TIMEOUT,
    )
    return parse_upstream(response, CourseFromArticleResponse)


@router.post("/ai/course-from-article/stream")
async def course_from_article_stream(
    body: CourseFromArticleRequest,
    user_id: UserId,
    settings: Settings,
    client: UpstreamClient,
) -> StreamingResponse:
    url = f"{settings.tutor_service_url}/internal/v1/tutor/studio/course-from-article/stream"
    request = client.build_request(
        "POST",
        url,
        headers={"X-User-Id": str(user_id)},
        json=body.model_dump(mode="json"),
        timeout=COURSE_FROM_ARTICLE_TIMEOUT,
    )
    response = await client.send(request, stream=True)
    if response.is_error:
        detail = upstream_detail(response)
        status_code = response.status_code
        await response.aclose()
        raise HTTPException(status_code=status_code, detail=detail)

    return StreamingResponse(
        stream_response_body(response),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
