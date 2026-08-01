from __future__ import annotations

import html
import re

from studio_contracts.studio_schemas import CourseArticleVideo

_MAX_VIDEOS = 8

_YT_ID = re.compile(
    r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:[^\"'\s]*&)?v=|embed/|shorts/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{6,})",
    re.IGNORECASE,
)
_VIMEO_ID = re.compile(
    r"(?:player\.)?vimeo\.com/(?:video/)?(\d{6,})",
    re.IGNORECASE,
)
_IFRAME_SRC = re.compile(
    r"<iframe[^>]+src\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
_HREF_SRC = re.compile(
    r"(?:href|src)\s*=\s*[\"'](https?://[^\"']+)[\"']",
    re.IGNORECASE,
)
_BARE_URL = re.compile(
    r"https?://(?:www\.)?(?:youtube(?:-nocookie)?\.com/(?:watch\?[^\"'\s<>]*|embed/[^\s\"'<>]+|shorts/[^\s\"'<>]+)|youtu\.be/[^\s\"'<>]+|vimeo\.com/[^\s\"'<>]+)",
    re.IGNORECASE,
)


def canonicalize_video_url(raw: str) -> CourseArticleVideo | None:
    text = html.unescape((raw or "").strip())
    if not text:
        return None
    if yt := _YT_ID.search(text):
        video_id = yt.group(1)
        return CourseArticleVideo(
            url=f"https://www.youtube.com/watch?v={video_id}",
            title=None,
        )
    if vimeo := _VIMEO_ID.search(text):
        return CourseArticleVideo(
            url=f"https://vimeo.com/{vimeo.group(1)}",
            title=None,
        )
    return None


def extract_video_refs(*chunks: str) -> list[CourseArticleVideo]:
    found: list[CourseArticleVideo] = []
    seen: set[str] = set()

    def add(candidate: str) -> None:
        video = canonicalize_video_url(candidate)
        if video is None or video.url in seen:
            return
        seen.add(video.url)
        found.append(video)

    for chunk in chunks:
        if not chunk:
            continue
        for match in _IFRAME_SRC.finditer(chunk):
            add(match.group(1))
        for match in _HREF_SRC.finditer(chunk):
            add(match.group(1))
        for match in _BARE_URL.finditer(chunk):
            add(match.group(0))
        if len(found) >= _MAX_VIDEOS:
            break
    return found[:_MAX_VIDEOS]
