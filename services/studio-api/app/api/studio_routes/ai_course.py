from __future__ import annotations

from typing import Annotated

from app.api.upstream_stream import COURSE_FROM_ARTICLE_TIMEOUT, stream_response_body
from app.config import StudioApiSettings, get_settings
from app.deps import UpstreamClient, UserId
from app.upstream import parse_upstream, upstream_detail
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from studio_contracts.studio_schemas import CourseFromArticleRequest, CourseFromArticleResponse

router = APIRouter()

type Settings = Annotated[StudioApiSettings, Depends(get_settings)]


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
