from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from app.domain.course_from_article.local_course.policy.heuristics import content_tokens
from app.domain.errors import TutorError
from app.domain.fetch_article_from_url.parsing.html import page_to_article_markdown
from app.domain.fetch_article_from_url.sources.url import (
    extract_http_urls,
    validate_public_http_url,
)

DEFAULT_WEB_ALLOWLIST: tuple[str, ...] = ()

_FETCH_TIMEOUT = 8.0
_MAX_REDIRECTS = 3
_SNIPPET_CHARS = 800
_MAX_BODY_BYTES = 48_000
MAX_GLOSSARY_FETCHES = 3
_THIN_EXCERPT = 160
_EXTERNAL_PREFIX = "external:"
_WS = re.compile(r"\s+")
_GLOSSARY_HEADERS = {
    "User-Agent": "TaskStudio-course-glossary/1.0",
    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
}


@dataclass
class GlossaryLookups:
    allowlist: tuple[str, ...]
    remaining: int = MAX_GLOSSARY_FETCHES
    seen_urls: set[str] = field(default_factory=set)


def parse_host_allowlist(
    raw: str,
    *,
    fallback: tuple[str, ...] = DEFAULT_WEB_ALLOWLIST,
) -> tuple[str, ...]:
    hosts = tuple(part.strip().casefold().lstrip(".") for part in raw.split(",") if part.strip())
    return hosts or fallback


def host_is_allowed(hostname: str, allowlist: tuple[str, ...]) -> bool:
    host = hostname.strip(".").casefold()
    if not host or not allowlist:
        return False
    return any(host == item or host.endswith(f".{item}") for item in allowlist)


def url_is_allowed(url: str, allowlist: tuple[str, ...]) -> bool:
    try:
        normalized = validate_public_http_url(url)
    except TutorError:
        return False
    host = urlparse(normalized).hostname or ""
    return host_is_allowed(host, allowlist)


def urls_from_sources(
    sources: list[dict[str, object]],
    article: str,
    allowlist: tuple[str, ...],
) -> list[str]:
    chunks = [article]
    for item in sources:
        chunks.extend((str(item.get("title") or ""), str(item.get("content") or "")))
    found = extract_http_urls(*chunks)
    return [url for url in found if url_is_allowed(url, allowlist)]


def term_needs_glossary(title: str, excerpt: str) -> bool:
    title_tokens = content_tokens(title)
    if not title_tokens:
        return False
    covered = title_tokens & content_tokens(excerpt)
    if len(excerpt.strip()) < _THIN_EXCERPT:
        return True
    return len(covered) < max(1, (len(title_tokens) + 1) // 2)


def snippet_fits_source(snippet: str, excerpt: str) -> bool:
    if not (snippet_tokens := content_tokens(snippet)):
        return False
    if len(excerpt.strip()) < _THIN_EXCERPT:
        return True
    return bool(snippet_tokens & content_tokens(excerpt))


def format_external_note(*, term: str, host: str, snippet: str) -> str:
    compact = _WS.sub(" ", snippet).strip()
    if not compact:
        return ""
    label = term.strip() or host
    return f"{_EXTERNAL_PREFIX} {label} — {compact} ({host})"


def append_external_note(content: str, note: str) -> str:
    text = (content or "").rstrip()
    extra = (note or "").strip()
    if not extra or extra in text:
        return text
    return f"{text}\n\n{extra}" if text else extra


def pick_url_for_chapter(title: str, urls: list[str], *, seen: set[str]) -> str | None:
    tokens = content_tokens(title)
    best: str | None = None
    best_score = 0
    for url in urls:
        if url in seen:
            continue
        blob = url.casefold()
        score = sum(token in blob for token in tokens)
        if score > best_score:
            best = url
            best_score = score
    return best if best_score > 0 else None


def _snippet_from_body(content_type: str, raw: str) -> str:
    try:
        _title, markdown = page_to_article_markdown(content_type, raw)
    except ValueError:
        return ""
    compact = _WS.sub(" ", markdown).strip()
    if len(compact) <= _SNIPPET_CHARS:
        return compact
    cut = compact[:_SNIPPET_CHARS]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.strip()


async def _read_limited_body(response: httpx.Response) -> str:
    chunks: list[bytes] = []
    size = 0
    try:
        async for chunk in response.aiter_bytes():
            chunks.append(chunk)
            size += len(chunk)
            if size >= _MAX_BODY_BYTES:
                break
    except (httpx.HTTPError, OSError, TimeoutError, UnicodeError):
        return ""
    raw = b"".join(chunks)[:_MAX_BODY_BYTES]
    encoding = response.encoding or "utf-8"
    return raw.decode(encoding, errors="replace")


async def _fetch_snippet(
    client: httpx.AsyncClient,
    url: str,
    *,
    allowlist: tuple[str, ...],
) -> str:
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        if not url_is_allowed(current, allowlist):
            return ""
        try:
            response = await client.get(
                current,
                headers=_GLOSSARY_HEADERS,
                follow_redirects=False,
                timeout=_FETCH_TIMEOUT,
            )
        except (httpx.HTTPError, OSError, TimeoutError):
            return ""
        try:
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    return ""
                current = urljoin(current, location)
                continue
            if response.status_code >= 400:
                return ""
            content_type = (response.headers.get("content-type") or "").lower()
            body = await _read_limited_body(response)
            return _snippet_from_body(content_type, body)
        finally:
            await response.aclose()
    return ""


async def lookup_chapter_note(
    client: httpx.AsyncClient,
    *,
    chapter: dict[str, str],
    sources: list[dict[str, object]],
    article: str,
    lookups: GlossaryLookups,
) -> str:
    if lookups.remaining <= 0 or not lookups.allowlist:
        return ""
    title = str(chapter.get("title") or "").strip()
    excerpt = str(chapter.get("source_excerpt") or "").strip()
    if not title or not term_needs_glossary(title, excerpt):
        return ""
    urls = urls_from_sources(sources, article, lookups.allowlist)
    chosen = pick_url_for_chapter(title, urls, seen=lookups.seen_urls)
    if chosen is None:
        return ""
    lookups.seen_urls.add(chosen)
    lookups.remaining -= 1
    snippet = await _fetch_snippet(client, chosen, allowlist=lookups.allowlist)
    if not snippet_fits_source(snippet, excerpt):
        return ""
    host = (urlparse(chosen).hostname or "").strip(".")
    return format_external_note(term=title, host=host, snippet=snippet)
