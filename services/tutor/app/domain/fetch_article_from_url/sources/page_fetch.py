from __future__ import annotations

import asyncio
import logging
from urllib.parse import urljoin, urlparse

import httpx
from app.domain.errors import TutorError
from app.domain.fetch_article_from_url.sources.challenge import looks_like_challenge_html
from app.domain.fetch_article_from_url.sources.url import (
    _BROWSER_HEADERS,
    _FETCH_TIMEOUT,
    _MAX_REDIRECTS,
    _READER_HEADERS,
    validate_public_http_url,
)
from app.domain.fetch_article_from_url.sources.wikipedia import wikipedia_rest_html_url
from app.domain.fetch_article_from_url.thresholds import MIN_ARTICLE_CHARS, SKIP_READER_CHARS
from fastapi import status

logger = logging.getLogger(__name__)

_WIKIMEDIA_HEADERS = {
    "User-Agent": "TaskStudioArticleFetch/1.0 (course-corpus; local-dev; contact=dev@localhost)",
    "Accept": "text/html; charset=utf-8, application/json;q=0.8,*/*;q=0.5",
    "Accept-Language": "en-US,en;q=0.9",
}


def _extracted_markdown(content_type: str, raw: str) -> str:
    from app.domain.fetch_article_from_url.parsing.html import page_to_article_markdown

    _title, markdown = page_to_article_markdown(content_type, raw)
    return markdown.strip()


def _extracted_len(content_type: str, raw: str) -> int:
    return len(_extracted_markdown(content_type, raw))


def _looks_like_page_chrome(markdown: str) -> bool:

    head = markdown[:1_200].casefold()
    markers = (
        "все потоки",
        "подписаться",
        "охват за 30",
        "[/ru/feed]",
        "войти",
        "рейтинг",
        "подписчики",
        "sign in",
        "log in",
        "subscribe",
        "newsletter",
        "cookie",
        "privacy policy",
        "skip to content",
        "all topics",
        "table of contents",
    )
    return sum(marker in head for marker in markers) >= 2


def _skip_reader(content_type: str, raw: str) -> bool:
    if looks_like_challenge_html(raw):
        return False
    markdown = _extracted_markdown(content_type, raw)
    if _looks_like_page_chrome(markdown):
        return False
    return len(markdown) >= SKIP_READER_CHARS


async def _fetch_direct(client: httpx.AsyncClient, url: str) -> tuple[str, str]:
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        validate_public_http_url(current)
        try:
            response = await client.get(
                current,
                headers=_BROWSER_HEADERS,
                follow_redirects=False,
                timeout=_FETCH_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise TutorError(status.HTTP_502_BAD_GATEWAY, "failed to fetch url") from exc

        if response.is_redirect:
            location = response.headers.get("location")
            if not location:
                raise TutorError(status.HTTP_502_BAD_GATEWAY, "redirect without location")
            current = urljoin(current, location)
            continue

        if response.status_code >= 400:
            raise TutorError(
                status.HTTP_502_BAD_GATEWAY,
                f"url returned HTTP {response.status_code}",
            )

        content_type = (response.headers.get("content-type") or "").lower()
        return content_type, response.text

    raise TutorError(status.HTTP_502_BAD_GATEWAY, "too many redirects")


def _validate_reader_base(reader_base: str) -> str:
    base = reader_base.strip().rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise TutorError(status.HTTP_500_INTERNAL_SERVER_ERROR, "invalid article reader base url")
    validate_public_http_url(f"{parsed.scheme}://{parsed.hostname}/")
    return base


async def _fetch_via_reader(
    client: httpx.AsyncClient,
    *,
    reader_base: str,
    source_url: str,
) -> tuple[str, str] | None:
    try:
        base = _validate_reader_base(reader_base)
    except TutorError:
        logger.warning("article reader base rejected by SSRF policy")
        return None

    proxy = f"{base}/{source_url}"
    try:
        response = await client.get(
            proxy,
            headers=_READER_HEADERS,
            follow_redirects=True,
            timeout=_FETCH_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        logger.warning("article reader fetch failed: %s", exc.__class__.__name__)
        return None

    if response.status_code >= 400:
        logger.warning("article reader returned HTTP %s", response.status_code)
        return None

    content_type = (response.headers.get("content-type") or "text/markdown").lower()
    body = response.text.strip()
    if len(body) < MIN_ARTICLE_CHARS or looks_like_challenge_html(body):
        return None
    return content_type, body


def _pick_richest(
    *candidates: tuple[str, str] | None,
) -> tuple[str, str] | None:
    best: tuple[str, str] | None = None
    best_len = -1
    for item in candidates:
        if item is None:
            continue
        length = _extracted_len(*item)
        if length > best_len:
            best = item
            best_len = length
    return best


async def _fetch_wikipedia_rest(
    client: httpx.AsyncClient,
    page_url: str,
) -> tuple[str, str] | None:

    _ = client
    rest = wikipedia_rest_html_url(page_url)
    if rest is None:
        return None
    curl_body = await asyncio.to_thread(_curl_wikipedia_html, rest)
    if curl_body and len(curl_body) >= MIN_ARTICLE_CHARS:
        return "text/html; charset=utf-8", curl_body
    return None


def _curl_wikipedia_html(rest_url: str) -> str | None:
    import shutil
    import subprocess

    curl = shutil.which("curl")
    if not curl:
        return None
    try:
        completed = subprocess.run(
            [
                curl,
                "-fsSL",
                "-A",
                _WIKIMEDIA_HEADERS["User-Agent"],
                "--max-time",
                "25",
                rest_url,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        logger.warning("wikipedia curl fallback failed: %s", exc.__class__.__name__)
        return None
    if completed.returncode != 0:
        return None
    body = (completed.stdout or "").strip()
    return body or None


async def fetch_page(
    client: httpx.AsyncClient,
    url: str,
    *,
    reader_base: str | None = None,
) -> tuple[str, str]:
    direct_error: TutorError | None = None
    direct: tuple[str, str] | None = None
    try:
        direct = await _fetch_direct(client, url)
    except TutorError as exc:
        direct_error = exc

    via_wiki: tuple[str, str] | None = None
    if direct is None and wikipedia_rest_html_url(url):
        logger.info("article fetch: trying Wikipedia REST for %s", url)
        via_wiki = await _fetch_wikipedia_rest(client, url)

    via_reader: tuple[str, str] | None = None
    want_reader = direct is None or not _skip_reader(*direct)
    if want_reader and reader_base and reader_base.strip():
        logger.info("article fetch: trying reader fallback for %s", url)
        via_reader = await _fetch_via_reader(
            client,
            reader_base=reader_base,
            source_url=url,
        )

    chosen = _pick_richest(direct, via_wiki, via_reader)
    if chosen is not None:
        return chosen
    if direct_error is not None:
        raise direct_error
    raise TutorError(status.HTTP_502_BAD_GATEWAY, "failed to fetch url")
