from __future__ import annotations

import re

from app.domain.fetch_article_from_url.media.images import ArticleImage, extract_image_refs

_MD_IMAGE = re.compile(
    r"!\[([^\]]*)\]\(\s*(https?://[^)\s]+)\s*(?:\"[^\"]*\"|'[^']*')?\s*\)",
    re.IGNORECASE,
)

_MATCH_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "into",
        "your",
        "you",
        "are",
        "was",
        "were",
        "have",
        "has",
        "how",
        "why",
        "what",
        "when",
        "где",
        "как",
        "что",
        "это",
        "для",
        "при",
        "или",
        "если",
        "также",
        "можно",
        "нужно",
        "server",
        "servers",
        "host",
        "hosts",
        "system",
        "systems",
        "app",
        "apps",
        "application",
        "applications",
        "image",
        "images",
        "figure",
        "figures",
        "diagram",
        "diagrams",
        "schema",
        "схема",
        "схемы",
        "рисунок",
        "рисунки",
        "глава",
        "chapter",
        "overview",
        "обзор",
        "введение",
        "introduction",
        "basics",
        "основы",
        "using",
        "между",
        "сравнение",
        "comparison",
        "versus",
        "vs",
    }
)

_MIN_TITLE_SCORE = 2
_MIN_TOTAL_SCORE = 3


def _coerce_image_rows(raw: object) -> list[ArticleImage]:
    if not isinstance(raw, list):
        return []
    out: list[ArticleImage] = []
    for item in raw:
        if isinstance(item, ArticleImage):
            out.append(item)
        elif isinstance(item, dict):
            url = str(item.get("url") or "").strip()
            if url.startswith(("http://", "https://")):
                out.append(ArticleImage(url=url, alt=str(item.get("alt") or "").strip()[:200]))
    return out


def images_from_sources(sources: list[dict[str, object]]) -> list[ArticleImage]:
    found: list[ArticleImage] = []
    seen: set[str] = set()
    for source in sources:
        for image in _coerce_image_rows(source.get("images")):
            if image.url in seen:
                continue
            seen.add(image.url)
            found.append(image)
        content = str(source.get("content") or "")
        for image in extract_image_refs(content):
            if image.url in seen:
                continue
            seen.add(image.url)
            found.append(image)
    return found


def _token_bits(text: str) -> set[str]:
    bits = set(re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{4,}", text.casefold()))
    return {bit for bit in bits if bit not in _MATCH_STOPWORDS}


def _chapter_image_score(
    image: ArticleImage,
    *,
    title_bits: set[str],
    excerpt_bits: set[str],
) -> tuple[int, int]:
    alt = image.alt.casefold()
    url_cf = image.url.casefold()
    title_score = 0
    for bit in title_bits:
        if bit in alt or bit in url_cf:
            title_score += 2
    excerpt_score = 0
    for bit in excerpt_bits:
        if bit in alt or bit in url_cf:
            excerpt_score += 1
    return title_score, title_score + excerpt_score


def _pick_chapter_images(
    chapter: dict[str, str],
    catalog: list[ArticleImage],
    *,
    per_chapter: int,
    used_globally: set[str],
) -> list[ArticleImage]:
    excerpt = chapter.get("source_excerpt") or ""
    picked: list[ArticleImage] = []
    seen: set[str] = set()
    for image in extract_image_refs(excerpt):
        if image.url in seen:
            continue
        seen.add(image.url)
        used_globally.add(image.url)
        picked.append(image)
    if len(picked) >= per_chapter:
        return picked[:per_chapter]

    title_bits = _token_bits(chapter.get("title") or "")
    excerpt_bits = _token_bits(excerpt)
    if not title_bits:
        return picked[:per_chapter]

    ranked: list[tuple[int, ArticleImage]] = []
    for image in catalog:
        if image.url in seen or image.url in used_globally:
            continue
        title_score, total = _chapter_image_score(
            image,
            title_bits=title_bits,
            excerpt_bits=excerpt_bits,
        )
        if title_score < _MIN_TITLE_SCORE or total < _MIN_TOTAL_SCORE:
            continue
        ranked.append((total, image))
    ranked.sort(key=lambda row: (-row[0], row[1].url))
    for _score, image in ranked:
        if len(picked) >= per_chapter:
            break
        seen.add(image.url)
        used_globally.add(image.url)
        picked.append(image)
    return picked[:per_chapter]


def attach_source_images_to_chapters(
    chapters: list[dict[str, str]],
    sources: list[dict[str, object]],
    *,
    per_chapter: int = 2,
) -> list[dict[str, str]]:
    catalog = images_from_sources(sources)
    if not catalog:
        return chapters
    used_globally: set[str] = set()
    out: list[dict[str, str]] = []
    for chapter in chapters:
        picked = _pick_chapter_images(
            chapter,
            catalog,
            per_chapter=per_chapter,
            used_globally=used_globally,
        )
        lines = [f"![{image.alt or 'figure'}]({image.url})" for image in picked]
        updated = dict(chapter)
        updated["source_images"] = "\n".join(lines)[:2_000]
        out.append(updated)
    return out


def filter_theory_images(
    content: str,
    *,
    allowed_urls: set[str],
    max_images: int = 2,
) -> tuple[str, list[str]]:
    if not content:
        return content, []
    kept_urls: list[str] = []
    used = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal used
        alt = match.group(1)
        url = match.group(2).strip()
        if url not in allowed_urls or used >= max_images:
            return ""
        used += 1
        if url not in kept_urls:
            kept_urls.append(url)
        return f"![{alt}]({url})"

    cleaned = _MD_IMAGE.sub(replace, content)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, kept_urls
