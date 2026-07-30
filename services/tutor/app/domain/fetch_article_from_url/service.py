from __future__ import annotations

import logging
import uuid

import httpx
from app.config import TutorConfig
from app.domain.context import fetch_user_settings
from app.domain.errors import TutorError
from app.domain.llm import resolve_llm_target
from fastapi import status
from studio_contracts.studio_schemas import FetchArticleFromUrlRequest, FetchArticleFromUrlResponse

from .article_parse import article_response_from_dict, parse_article_json
from .extract_llm import extract_article_via_llm
from .html import page_to_plaintext
from .page_fetch import fetch_page
from .plaintext_fallback import plaintext_article_response
from .url import validate_public_http_url
from .videos import extract_video_refs

logger = logging.getLogger(__name__)


_page_to_plaintext = page_to_plaintext
_fetch_page = fetch_page
_parse_article_json = parse_article_json
_article_response_from_dict = article_response_from_dict


async def fetch_article_from_url(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    user_id: uuid.UUID,
    body: FetchArticleFromUrlRequest,
) -> FetchArticleFromUrlResponse:
    try:
        source_url = validate_public_http_url(body.url)
        content_type, raw = await fetch_page(client, source_url)
        page_videos = extract_video_refs(raw)
        page_title, plaintext = page_to_plaintext(content_type, raw)
        if len(plaintext.strip()) < 80:
            raise TutorError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "page has no readable article text",
            )

        user_settings = await fetch_user_settings(client, config, user_id)
        target = resolve_llm_target(
            config,
            provider_url=user_settings.provider_url,
            api_key_encrypted=user_settings.api_key_encrypted,
            model=user_settings.model,
        )
        if target is None:
            logger.info("article extract: no LLM target, using plaintext fallback")
            return plaintext_article_response(
                source_url=source_url,
                page_title=page_title,
                plaintext=plaintext,
                page_videos=page_videos,
            )

        try:
            return await extract_article_via_llm(
                client,
                config,
                target=target,
                source_url=source_url,
                page_title=page_title,
                plaintext=plaintext,
                page_videos=page_videos,
            )
        except TutorError as exc:
            if exc.status_code >= 500:
                logger.warning(
                    "article LLM extract failed (%s), falling back to plaintext",
                    exc.detail,
                )
                return plaintext_article_response(
                    source_url=source_url,
                    page_title=page_title,
                    plaintext=plaintext,
                    page_videos=page_videos,
                )
            raise
    except TutorError:
        raise
    except Exception as exc:
        raise TutorError(
            status.HTTP_502_BAD_GATEWAY,
            f"article extract failed: {exc.__class__.__name__}",
        ) from exc


__all__ = [
    "fetch_article_from_url",
    "validate_public_http_url",
    "extract_video_refs",
    "_page_to_plaintext",
    "_parse_article_json",
]
