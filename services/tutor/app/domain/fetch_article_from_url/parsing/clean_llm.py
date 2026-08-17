from __future__ import annotations

import logging

import httpx
from app.config import TutorConfig
from app.domain.fetch_article_from_url.parsing.article_parse import article_response_from_dict
from app.domain.fetch_article_from_url.parsing.dechrome import apply_dechrome, parse_dechrome_plan
from app.domain.fetch_article_from_url.thresholds import MIN_ARTICLE_CHARS
from app.domain.json_util.repair import parse_or_repair_json
from app.domain.llm import LlmTarget, complete_chat_completion, is_ollama_target
from app.domain.ollama.defaults import OLLAMA_NUM_CTX
from app.domain.prompt_compose import article_from_url_system_prompt

logger = logging.getLogger(__name__)

_CHUNK_CHARS = 8_000
_ANALYZE_MAX_TOKENS = 2_500
_RESCUE_SOURCE_CHARS = 24_000
_RESCUE_MAX_TOKENS = 8_000

_RESCUE_SYSTEM = (
    "You extract the main article from a page dump for Task Studio. "
    'Return JSON only: {"title":"...","content":"..."} where content is '
    "markdown of the article body. Copy wording from the source; do not invent "
    "facts, APIs, or sections. Drop ads, nav, comments, related posts. "
    "Keep code blocks and headings. content must be the full article, not a summary."
)


def _windows(markdown: str) -> list[str]:
    text = markdown.strip()
    if len(text) <= _CHUNK_CHARS:
        return [text]
    windows: list[str] = []
    step = _CHUNK_CHARS - 400
    pos = 0
    while pos < len(text):
        windows.append(text[pos : pos + _CHUNK_CHARS])
        if pos + _CHUNK_CHARS >= len(text):
            break
        pos += step
    return windows


async def _analyze_window(
    client: httpx.AsyncClient,
    config: TutorConfig,
    target: LlmTarget,
    *,
    source_url: str,
    page_title: str,
    window: str,
    window_index: int,
    window_total: int,
) -> tuple[str, list[str]]:
    compact = is_ollama_target(config, target)
    system_prompt = article_from_url_system_prompt(compact=compact)
    user_message = (
        f"Source URL: {source_url}\n"
        f"Title hint: {page_title or '(none)'}\n"
        f"Draft window {window_index}/{window_total}\n\n"
        "<article_draft_markdown>\n"
        f"{window}\n"
        "</article_draft_markdown>\n\n"
        "Analyze this draft window. JSON only with remove_excerpts "
        "(exact substrings to delete: ads, promos, chrome). "
        "Do not rewrite the article."
    )
    raw = await complete_chat_completion(
        client,
        target,
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.1,
        max_tokens=_ANALYZE_MAX_TOKENS,
        num_ctx=OLLAMA_NUM_CTX if compact else None,
    )
    parsed = await parse_or_repair_json(
        client,
        target,
        raw=raw,
        hint='article_dechrome: {"title":"","remove_excerpts":["..."]}',
        max_tokens=min(OLLAMA_NUM_CTX, 2_000),
        num_ctx=OLLAMA_NUM_CTX if compact else None,
    )
    return ("", []) if parsed is None else parse_dechrome_plan(parsed)


async def polish_article_markdown(
    client: httpx.AsyncClient,
    config: TutorConfig,
    target: LlmTarget,
    *,
    source_url: str,
    page_title: str,
    markdown: str,
) -> tuple[str, str]:
    windows = _windows(markdown)

    if is_ollama_target(config, target) and len(windows) > 1:
        windows = windows[:1]
    title_vote = page_title
    excerpts: list[str] = []
    for index, window in enumerate(windows, start=1):
        try:
            title, chunk_excerpts = await _analyze_window(
                client,
                config,
                target,
                source_url=source_url,
                page_title=page_title,
                window=window,
                window_index=index,
                window_total=len(windows),
            )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.warning(
                "article analyze window %s failed: %s",
                index,
                exc.__class__.__name__,
            )
            continue
        if title.strip():
            title_vote = title.strip()
        excerpts.extend(chunk_excerpts)

    if not excerpts:
        return title_vote, markdown

    cleaned, removed = apply_dechrome(
        markdown,
        remove_excerpts=excerpts,
        title_hint=title_vote,
    )
    if removed:
        logger.info(
            "article dechrome: removed %s chars via %s excerpts",
            removed,
            len(excerpts),
        )
    return title_vote, cleaned


async def rescue_article_from_page(
    client: httpx.AsyncClient,
    config: TutorConfig,
    target: LlmTarget,
    *,
    source_url: str,
    page_title: str,
    page_dump: str,
) -> tuple[str, str]:
    dump = page_dump.strip()
    if len(dump) > _RESCUE_SOURCE_CHARS:
        dump = dump[:_RESCUE_SOURCE_CHARS]
    compact = is_ollama_target(config, target)
    user_message = (
        f"Source URL: {source_url}\n"
        f"Title hint: {page_title or '(none)'}\n\n"
        "<page_dump>\n"
        f"{dump}\n"
        "</page_dump>\n\n"
        "Extract the article as JSON {title, content}."
    )
    raw = await complete_chat_completion(
        client,
        target,
        system_prompt=_RESCUE_SYSTEM,
        user_message=user_message,
        temperature=0.1,
        max_tokens=_RESCUE_MAX_TOKENS,
        num_ctx=OLLAMA_NUM_CTX if compact else None,
    )
    parsed = await parse_or_repair_json(
        client,
        target,
        raw=raw,
        hint='article_rescue: {"title":"","content":""}',
        max_tokens=min(OLLAMA_NUM_CTX, 4_000),
        num_ctx=OLLAMA_NUM_CTX if compact else None,
    )
    if parsed is None:
        raise ValueError("rescue llm returned no json")
    response = article_response_from_dict(
        parsed,
        fallback_title=page_title,
        source_url=source_url,
    )
    if len(response.content.strip()) < MIN_ARTICLE_CHARS:
        raise ValueError("rescue article too short")
    return response.title, response.content
