from __future__ import annotations

from app.domain.errors import TutorError
from app.domain.fetch_article_from_url.media.videos import MAX_VIDEOS, extract_video_refs
from fastapi import status
from studio_contracts.api.studio_schemas import CourseArticleVideo, FetchArticleFromUrlResponse


def parse_article_json(
    raw: str,
    *,
    fallback_title: str,
    source_url: str,
    videos: list[CourseArticleVideo] | None = None,
) -> FetchArticleFromUrlResponse:
    from app.domain.json_util.repair import extract_json_object

    parsed = extract_json_object(raw)
    if parsed is None:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "tutor returned invalid JSON")
    return article_response_from_dict(
        parsed,
        fallback_title=fallback_title,
        source_url=source_url,
        videos=videos,
    )


def article_response_from_dict(
    parsed: dict[str, object],
    *,
    fallback_title: str,
    source_url: str,
    videos: list[CourseArticleVideo] | None = None,
) -> FetchArticleFromUrlResponse:
    title = str(parsed.get("title") or fallback_title or source_url).strip()
    content = str(parsed.get("content") or "").strip()
    if len(content) < 40:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "extracted article too short")
    merged = extract_video_refs(content, *(video.url for video in (videos or [])))
    if videos:
        ordered: list[CourseArticleVideo] = []
        seen: set[str] = set()
        for video in [*videos, *merged]:
            if video.url in seen:
                continue
            seen.add(video.url)
            ordered.append(video)
            if len(ordered) >= MAX_VIDEOS:
                break
        merged = ordered
    return FetchArticleFromUrlResponse(
        title=title[:240],
        content=content,
        source_url=source_url,
        videos=merged,
    )
