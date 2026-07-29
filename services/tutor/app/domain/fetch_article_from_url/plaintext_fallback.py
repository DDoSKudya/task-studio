from __future__ import annotations

import re

from studio_contracts.studio_schemas import CourseArticleVideo, FetchArticleFromUrlResponse

from .article_parse import article_response_from_dict

_MAX_FALLBACK_CHARS = 80_000


def plaintext_article_response(
    *,
    source_url: str,
    page_title: str,
    plaintext: str,
    page_videos: list[CourseArticleVideo] | None = None,
) -> FetchArticleFromUrlResponse:
                                                                                 
    body = re.sub(r"\n{3,}", "\n\n", plaintext.strip())
    if len(body) > _MAX_FALLBACK_CHARS:
        body = body[:_MAX_FALLBACK_CHARS]
    title = (page_title or "").strip() or source_url
    content = f"# {title}\n\n{body}" if not body.startswith("#") else body
    return article_response_from_dict(
        {"title": title, "content": content},
        fallback_title=title,
        source_url=source_url,
        videos=page_videos,
    )
