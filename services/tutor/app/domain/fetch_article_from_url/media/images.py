from __future__ import annotations

import html
import re
from dataclasses import dataclass

_MAX_IMAGES = 16

_MD_IMAGE = re.compile(
    r"!\[([^\]]*)\]\(\s*(https?://[^)\s]+)\s*(?:\"[^\"]*\"|'[^']*')?\s*\)",
    re.IGNORECASE,
)
_HTML_IMG = re.compile(
    r"<img\b[^>]*\bsrc\s*=\s*[\"'](https?://[^\"']+)[\"'][^>]*>",
    re.IGNORECASE,
)
_HTML_ALT = re.compile(r"\balt\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE)

_JUNK_URL = re.compile(
    r"(?:favicon|sprite|emoji|avatar|logo|badge|icon[-_/]|pixel|tracking|"
    r"1x1|spacer|blank\.gif|/ads?/|doubleclick|googlesyndication|"
    r"gravatar\.com|wp-includes/|emoji-)",
    re.IGNORECASE,
)
_IMAGE_EXT = re.compile(
    r"\.(?:png|jpe?g|gif|webp|svg|avif|bmp)(?:\?|#|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ArticleImage:
    url: str
    alt: str = ""


def _looks_like_image_url(url: str) -> bool:
    if _JUNK_URL.search(url):
        return False
    if _IMAGE_EXT.search(url):
        return True
    lowered = url.casefold()
    return any(
        token in lowered
        for token in (
            "/images/",
            "/image/",
            "/media/",
            "/uploads/",
            "/static/",
            "imgix.net",
            "cloudinary.com",
            "digitaloceanspaces.com",
            "habrastorage.org",
            "githubusercontent.com",
        )
    )


def extract_image_refs(*chunks: str) -> list[ArticleImage]:
    found: list[ArticleImage] = []
    seen: set[str] = set()

    def add(url: str, alt: str = "") -> None:
        cleaned = html.unescape((url or "").strip())
        if cleaned.startswith("//"):
            cleaned = f"https:{cleaned}"
        if not cleaned.startswith(("http://", "https://")):
            return
        if cleaned in seen or not _looks_like_image_url(cleaned):
            return
        seen.add(cleaned)
        found.append(ArticleImage(url=cleaned, alt=html.unescape((alt or "").strip())[:200]))

    for chunk in chunks:
        if not chunk:
            continue
        for match in _MD_IMAGE.finditer(chunk):
            add(match.group(2), match.group(1))
        for match in _HTML_IMG.finditer(chunk):
            tag = match.group(0)
            alt_match = _HTML_ALT.search(tag)
            add(match.group(1), alt_match.group(1) if alt_match else "")
        if len(found) >= _MAX_IMAGES:
            break
    return found[:_MAX_IMAGES]
