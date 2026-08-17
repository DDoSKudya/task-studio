from __future__ import annotations

import re

from app.domain.fetch_article_from_url.parsing.article_parse import article_response_from_dict
from studio_contracts.api.studio_schemas import CourseArticleVideo, FetchArticleFromUrlResponse


def plaintext_article_response(
    *,
    source_url: str,
    page_title: str,
    plaintext: str,
    page_videos: list[CourseArticleVideo] | None = None,
) -> FetchArticleFromUrlResponse:
    body = re.sub(r"\n{3,}", "\n\n", plaintext.strip())
    title = (page_title or "").strip() or source_url
    content = f"# {title}\n\n{body}" if title and not body.lstrip().startswith("#") else body
    return article_response_from_dict(
        {"title": title, "content": content},
        fallback_title=title,
        source_url=source_url,
        videos=page_videos,
    )
