from __future__ import annotations

import logging
import uuid

import httpx
from app.config import TutorConfig
from app.domain.context import fetch_user_settings
from app.domain.errors import TutorError
from app.domain.llm import LlmTarget, resolve_llm_target
from fastapi import status
from studio_contracts.studio_schemas import (
    FetchArticleBatchItem,
    FetchArticleFromUrlRequest,
    FetchArticleFromUrlResponse,
    FetchArticlesFromUrlsRequest,
    FetchArticlesFromUrlsResponse,
)

from .article_parse import article_response_from_dict, parse_article_json
from .clean_llm import polish_article_markdown, rescue_article_from_page
from .html import page_to_article_markdown, page_to_plaintext
from .page_fetch import fetch_page
from .plaintext_fallback import plaintext_article_response
from .thresholds import MIN_ARTICLE_CHARS
from .url import _MAX_BATCH_URLS, extract_http_urls, validate_public_http_url
from .videos import extract_video_refs

logger = logging.getLogger(__name__)

_page_to_plaintext = page_to_plaintext
_page_to_article_markdown = page_to_article_markdown
_fetch_page = fetch_page
_parse_article_json = parse_article_json
_article_response_from_dict = article_response_from_dict


async def _resolve_optional_target(
    client: httpx.AsyncClient,
    config: TutorConfig,
    user_id: uuid.UUID,
) -> LlmTarget | None:
    try:
        user_settings = await fetch_user_settings(client, config, user_id)
        return resolve_llm_target(
            config,
            provider_url=user_settings.provider_url,
            api_key_encrypted=user_settings.api_key_encrypted,
            model=user_settings.model,
            task="chat",
        )
    except TutorError:
        return None


def _plaintext_if_richer(
    content_type: str,
    raw: str,
    *,
    page_title: str,
    markdown: str,
) -> tuple[str, str]:
    body_len = len(markdown.strip())
    if body_len >= MIN_ARTICLE_CHARS:
        return page_title, markdown
    plain_title, plaintext = page_to_plaintext(content_type, raw)
    if len(plaintext.strip()) <= body_len:
        return page_title, markdown
    logger.info("article ingest: plaintext fallback (%s chars)", len(plaintext.strip()))
    return plain_title or page_title, plaintext


async def _rescue_if_thin(
    client: httpx.AsyncClient,
    config: TutorConfig,
    target: LlmTarget | None,
    *,
    source_url: str,
    content_type: str,
    raw: str,
    page_title: str,
    markdown: str,
) -> tuple[str, str]:
    if len(markdown.strip()) >= MIN_ARTICLE_CHARS or target is None:
        return page_title, markdown
    dump = raw if len(raw) < 30_000 else page_to_plaintext(content_type, raw)[1]
    try:
        title, body = await rescue_article_from_page(
            client,
            config,
            target,
            source_url=source_url,
            page_title=page_title,
            page_dump=dump,
        )
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("article LLM rescue failed (%s)", exc.__class__.__name__)
        return page_title, markdown
    logger.info("article ingest: LLM rescue (%s chars) from %s", len(body.strip()), source_url)
    return title, body


async def _maybe_dechrome(
    client: httpx.AsyncClient,
    config: TutorConfig,
    target: LlmTarget | None,
    *,
    source_url: str,
    page_title: str,
    markdown: str,
) -> tuple[str, str]:
    if target is None or len(markdown.strip()) < MIN_ARTICLE_CHARS:
        return page_title, markdown
    try:
        return await polish_article_markdown(
            client,
            config,
            target,
            source_url=source_url,
            page_title=page_title,
            markdown=markdown,
        )
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning(
            "article LLM dechrome failed (%s), keeping deterministic draft",
            exc.__class__.__name__,
        )
        return page_title, markdown


async def fetch_article_from_url(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: FetchArticleFromUrlRequest,
) -> FetchArticleFromUrlResponse:
    try:
        source_url = validate_public_http_url(body.url)
        content_type, raw = await fetch_page(
            client,
            source_url,
            reader_base=config.article_fetch_reader_url or None,
        )
        page_videos = extract_video_refs(raw)
        page_title, markdown = page_to_article_markdown(content_type, raw)
        page_title, markdown = _plaintext_if_richer(
            content_type, raw, page_title=page_title, markdown=markdown
        )
        target = await _resolve_optional_target(client, config, user_id)
        page_title, markdown = await _rescue_if_thin(
            client,
            config,
            target,
            source_url=source_url,
            content_type=content_type,
            raw=raw,
            page_title=page_title,
            markdown=markdown,
        )
        if len(markdown.strip()) < MIN_ARTICLE_CHARS:
            raise TutorError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "page has no readable article text",
            )

        logger.info(
            "article ingest: markdown (%s chars) from %s",
            len(markdown.strip()),
            source_url,
        )
        final_title, final_markdown = await _maybe_dechrome(
            client,
            config,
            target,
            source_url=source_url,
            page_title=page_title,
            markdown=markdown,
        )
        if len(final_markdown.strip()) < MIN_ARTICLE_CHARS:
            final_title, final_markdown = page_title, markdown

        return plaintext_article_response(
            source_url=source_url,
            page_title=final_title or page_title,
            plaintext=final_markdown,
            page_videos=page_videos,
        )
    except TutorError:
        raise
    except (
        httpx.HTTPError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        raise TutorError(
            status.HTTP_502_BAD_GATEWAY,
            f"article extract failed: {exc.__class__.__name__}",
        ) from exc


def _resolve_batch_urls(body: FetchArticlesFromUrlsRequest) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()
    for raw in body.urls:
        text = str(raw or "").strip()
        if not text:
            continue
        for url in extract_http_urls(text, limit=_MAX_BATCH_URLS):
            if url in seen:
                continue
            seen.add(url)
            collected.append(url)
            if len(collected) >= _MAX_BATCH_URLS:
                return collected
    if body.text:
        for url in extract_http_urls(body.text, limit=_MAX_BATCH_URLS):
            if url in seen:
                continue
            seen.add(url)
            collected.append(url)
            if len(collected) >= _MAX_BATCH_URLS:
                break
    return collected


async def fetch_articles_from_urls(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: FetchArticlesFromUrlsRequest,
) -> FetchArticlesFromUrlsResponse:
    urls = _resolve_batch_urls(body)
    if not urls:
        raise TutorError(status.HTTP_422_UNPROCESSABLE_ENTITY, "no usable article urls")

    results: list[FetchArticleBatchItem] = []
    ok_count = 0
    for index, url in enumerate(urls):
        try:
            article = await fetch_article_from_url(
                client,
                config,
                user_id=user_id,
                body=FetchArticleFromUrlRequest(url=url),
            )
            ok_count += 1
            results.append(
                FetchArticleBatchItem(
                    url=url,
                    ok=True,
                    index=index,
                    title=article.title,
                    content=article.content,
                    source_url=article.source_url,
                    videos=list(article.videos or []),
                )
            )
        except TutorError as exc:
            detail = str(getattr(exc, "detail", "") or exc)
            results.append(
                FetchArticleBatchItem(
                    url=url,
                    ok=False,
                    index=index,
                    error=detail[:500] or "fetch failed",
                )
            )

    return FetchArticlesFromUrlsResponse(
        results=results,
        total=len(results),
        ok_count=ok_count,
        error_count=len(results) - ok_count,
    )


__all__ = [
    "extract_http_urls",
    "fetch_article_from_url",
    "fetch_articles_from_urls",
    "validate_public_http_url",
    "extract_video_refs",
    "_page_to_plaintext",
    "_page_to_article_markdown",
    "_parse_article_json",
]
