from __future__ import annotations

import re

from app.domain.fetch_article_from_url.images import ArticleImage, extract_image_refs

_MD_IMAGE = re.compile(
    r"!\[([^\]]*)\]\(\s*(https?://[^)\s]+)\s*(?:\"[^\"]*\"|'[^']*')?\s*\)",
    re.IGNORECASE,
)


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


def attach_source_images_to_chapters(
    chapters: list[dict[str, str]],
    sources: list[dict[str, object]],
    *,
    per_chapter: int = 4,
) -> list[dict[str, str]]:
    """Pick figures per chapter: prefer those mentioned in the excerpt, else source pool."""
    catalog = images_from_sources(sources)
    if not catalog:
        return chapters
    out: list[dict[str, str]] = []
    for chapter in chapters:
        excerpt = chapter.get("source_excerpt") or ""
        local = extract_image_refs(excerpt)
        picked: list[ArticleImage] = []
        seen: set[str] = set()
        for image in local:
            if image.url in seen:
                continue
            seen.add(image.url)
            picked.append(image)
        if len(picked) < per_chapter:
            title_text = (chapter.get("title") or "").casefold()
            title_bits = set(re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]{3,}", title_text))
            ranked: list[tuple[int, ArticleImage]] = []
            for image in catalog:
                if image.url in seen:
                    continue
                alt = image.alt.casefold()
                score = sum(1 for bit in title_bits if bit in alt or bit in image.url.casefold())
                ranked.append((score, image))
            ranked.sort(key=lambda row: (-row[0], row[1].url))
            for _score, image in ranked:
                if len(picked) >= per_chapter:
                    break
                seen.add(image.url)
                picked.append(image)
        lines = [f"![{image.alt or 'figure'}]({image.url})" for image in picked[:per_chapter]]
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
    """Keep only allowlisted markdown images (≤max); drop invented URLs."""
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
