from __future__ import annotations

from app.domain.errors import TutorError
from app.domain.fetch_article_from_url import extract_image_refs, extract_video_refs
from fastapi import status
from studio_contracts.studio_schemas import CourseArticleVideo, CourseFromArticleRequest

from .textutil_scalars import (
    _as_str,
    _combined_corpus,
    _excerpt_balanced,
    _join_string_list,
    _slug,
    _string_list,
)

__all__ = [
    "_as_str",
    "_articles_from_body",
    "_combined_corpus",
    "_excerpt_balanced",
    "_join_string_list",
    "_slug",
    "_string_list",
    "_video_steps_from_sources",
]


def _image_rows(content: str) -> list[dict[str, str]]:
    return [{"url": item.url, "alt": item.alt} for item in extract_image_refs(content)]


def _articles_from_body(body: CourseFromArticleRequest) -> list[dict[str, object]]:
    if body.articles:
        rows: list[dict[str, object]] = []
        for index, item in enumerate(body.articles):
            content = item.content.strip()
            if len(content) < 40:
                continue
            title = (item.title or "").strip() or f"Article {index + 1}"
            videos = list(item.videos or [])
            if not videos:
                videos = extract_video_refs(content)
            else:
                videos = extract_video_refs(
                    "\n".join(video.url for video in videos),
                    content,
                )
            rows.append(
                {
                    "title": title,
                    "content": content,
                    "videos": videos,
                    "images": _image_rows(content),
                }
            )
        if not rows:
            raise TutorError(status.HTTP_422_UNPROCESSABLE_ENTITY, "no usable articles")
        return rows
    text = (body.article or "").strip()
    if len(text) < 80:
        raise TutorError(status.HTTP_422_UNPROCESSABLE_ENTITY, "article too short")
    return [
        {
            "title": (body.title or "Article").strip() or "Article",
            "content": text,
            "videos": extract_video_refs(text),
            "images": _image_rows(text),
        }
    ]


def _video_steps_from_sources(sources: list[dict[str, object]]) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    seen: set[str] = set()
    for source in sources:
        title = str(source.get("title") or "Article")
        raw_videos = source.get("videos") or []
        if not isinstance(raw_videos, list):
            continue
        for index, item in enumerate(raw_videos):
            url = ""
            video_title = None
            if isinstance(item, CourseArticleVideo):
                url = item.url.strip()
                video_title = item.title
            elif isinstance(item, dict):
                url = str(item.get("url") or "").strip()
                video_title = _as_str(item.get("title"))
            if not url or url in seen:
                continue
            seen.add(url)
            step_id = _slug(f"video-{title}-{index + 1}")
            if not step_id.startswith("video"):
                step_id = f"video-{step_id}"
            steps.append(
                {
                    "id": step_id,
                    "kind": "video",
                    "title": video_title or f"{title} — video {index + 1}",
                    "video_url": url,
                }
            )
            if len(steps) >= 8:
                return steps
    return steps
