from __future__ import annotations

from app.domain.fetch_article_from_url.media.images import extract_image_refs
from app.domain.fetch_article_from_url.media.videos import extract_video_refs
from app.domain.fetch_article_from_url.parsing.html import (
    page_to_article_markdown,
    page_to_plaintext,
)
from app.domain.fetch_article_from_url.sources.service import (
    fetch_article_from_url,
    fetch_articles_from_urls,
    parse_article_json,
)
from app.domain.fetch_article_from_url.sources.url import (
    extract_http_urls,
    is_blocked_host,
    validate_public_http_url,
)

__all__ = [
    "extract_http_urls",
    "extract_image_refs",
    "extract_video_refs",
    "fetch_article_from_url",
    "fetch_articles_from_urls",
    "validate_public_http_url",
    "is_blocked_host",
    "page_to_plaintext",
    "page_to_article_markdown",
    "parse_article_json",
]
