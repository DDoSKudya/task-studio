from __future__ import annotations

import re

from studio_contracts.studio_schemas import CourseArticleVideo, FetchArticleFromUrlResponse

from .article_parse import article_response_from_dict


def plaintext_article_response(
    *,
    source_url: str,
    page_title: str,
    plaintext: str,
    page_videos: list[CourseArticleVideo] | None = None,
) -> FetchArticleFromUrlResponse:
    """Собрать ответ ingest: полный markdown статьи (без сжатия)."""
    body = re.sub(r"\n{3,}", "\n\n", plaintext.strip())
    title = (page_title or "").strip() or source_url
    content = f"# {title}\n\n{body}" if title and not body.lstrip().startswith("#") else body
    return article_response_from_dict(
        {"title": title, "content": content},
        fallback_title=title,
        source_url=source_url,
        videos=page_videos,
    )
