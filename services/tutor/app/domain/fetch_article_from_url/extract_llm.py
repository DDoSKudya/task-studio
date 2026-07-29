from __future__ import annotations

import httpx
from app.config import TutorConfig
from app.domain.errors import TutorError
from app.domain.llm import LlmTarget, complete_chat_completion, is_ollama_target
from app.domain.prompt_compose import article_from_url_system_prompt
from fastapi import status
from studio_contracts.studio_schemas import CourseArticleVideo, FetchArticleFromUrlResponse

from .article_parse import article_response_from_dict


async def extract_article_via_llm(
    client: httpx.AsyncClient,
    config: TutorConfig,
    *,
    target: LlmTarget,
    source_url: str,
    page_title: str,
    plaintext: str,
    page_videos: list[CourseArticleVideo],
) -> FetchArticleFromUrlResponse:
    user_message = (
        f"Source URL: {source_url}\n"
        f"Detected title hint: {page_title or '(none)'}\n\n"
        "<page_plaintext>\n"
        f"{plaintext}\n"
        "</page_plaintext>\n\n"
        "Extract a verbatim markdown article from the page content. JSON only."
    )
    compact = is_ollama_target(config, target)
    try:
        raw_llm = await complete_chat_completion(
            client,
            target,
            system_prompt=article_from_url_system_prompt(compact=compact),
            user_message=user_message,
            temperature=0.1,
            max_tokens=8192,
        )
    except (httpx.HTTPError, ValueError) as exc:
        detail = str(exc).strip() or "tutor provider error"
        raise TutorError(status.HTTP_502_BAD_GATEWAY, detail) from exc

    from app.domain.json_util.repair import parse_or_repair_json
    from app.domain.ollama.defaults import OLLAMA_NUM_CTX

    parsed = await parse_or_repair_json(
        client,
        target,
        raw=raw_llm,
        hint='article_from_url: {"title":"...","content":"markdown..."}',
        max_tokens=OLLAMA_NUM_CTX,
        num_ctx=OLLAMA_NUM_CTX if compact else None,
    )
    if parsed is None:
        raise TutorError(status.HTTP_502_BAD_GATEWAY, "tutor returned invalid JSON")
    return article_response_from_dict(
        parsed,
        fallback_title=page_title,
        source_url=source_url,
        videos=page_videos,
    )
