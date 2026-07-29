from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from .url import _MAX_RAW_CHARS


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "noscript", "svg", "iframe"}:
            self._skip_depth += 1
            return
        if lower == "title":
            self._in_title = True
        if lower in {"p", "div", "section", "article", "br", "li", "h1", "h2", "h3", "h4", "tr"}:
            self._chunks.append("\n")
        if lower in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "noscript", "svg", "iframe"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if lower == "title":
            self._in_title = False
        if lower in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "tr"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title and not self.title:
            self.title = text
        self._chunks.append(text + " ")

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = html.unescape(raw)
        raw = re.sub(r"[ \t]+\n", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        raw = re.sub(r"[ \t]{2,}", " ", raw)
        return raw.strip()


def page_to_plaintext(content_type: str, raw: str) -> tuple[str, str]:
    if "html" in content_type or "<html" in raw[:500].lower() or "<!doctype" in raw[:200].lower():
        parser = TextExtractor()
        try:
            parser.feed(raw)
            parser.close()
        except Exception:
            text = re.sub(r"<[^>]+>", " ", raw)
            return "", text[:_MAX_RAW_CHARS]
        return parser.title, parser.text()[:_MAX_RAW_CHARS]
    return "", raw.strip()[:_MAX_RAW_CHARS]


_page_to_plaintext = page_to_plaintext
_TextExtractor = TextExtractor
