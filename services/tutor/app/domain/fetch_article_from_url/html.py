from __future__ import annotations

import html
import re
from html.parser import HTMLParser

# Селекторы тела статьи (сильнее, чем голый <main>/<article> с шапкой).
_BODY_CLASS_HINTS = (
    "tm-article-body",
    "article-formatted-body",
    "article__body",
    "article-body",
    "post__text",
    "post_content",
    "entry-content",
    "content-body",
    "news-content",
    "post-content-body",
)

_OPEN_TAG = re.compile(r"(?is)<(article|main|div|section)\b([^>]*)>")
_ID_ATTR = re.compile(r"""(?is)\bid\s*=\s*["']([^"']+)["']""")
_CLASS_ATTR = re.compile(r"""(?is)\bclass\s*=\s*["']([^"']+)["']""")

_READER_TITLE = re.compile(r"(?im)^Title:\s*(.+)$")
_READER_MD_MARK = re.compile(r"(?im)^Markdown Content:\s*$")


class TextExtractor(HTMLParser):
    """Грубый plaintext — только для антибот-эвристик."""

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
        self._chunks.append(f"{text} ")

    def text(self) -> str:
        raw = "".join(self._chunks)
        raw = html.unescape(raw)
        raw = re.sub(r"[ \t]+\n", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        raw = re.sub(r"[ \t]{2,}", " ", raw)
        return raw.strip()


class MarkdownConverter(HTMLParser):
    """HTML фрагмента статьи → markdown без сжатия."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self._in_pre = False
        self._in_code = False
        self._code_lang = ""
        self._code_buf: list[str] = []
        self._link_href: str | None = None
        self._link_buf: list[str] = []
        self._list_stack: list[str] = []
        self.title = ""
        self._in_title = False
        self._pending_heading: str | None = None
        self._heading_buf: list[str] = []

    def _emit(self, text: str) -> None:
        if text:
            self._parts.append(text)

    def _attr(self, attrs: list[tuple[str, str | None]], name: str) -> str:
        return next(
            (value.strip() for key, value in attrs if key.lower() == name and value),
            "",
        )

    def _start_code(self, attrs: list[tuple[str, str | None]]) -> None:
        class_name = self._attr(attrs, "class")
        lang = next(
            (
                token.removeprefix("language-")
                for token in class_name.split()
                if token.startswith("language-")
            ),
            "",
        )
        self._in_code = True
        self._code_buf = []
        if self._in_pre:
            self._code_lang = lang

    def _start_link_or_img(self, lower: str, attrs: list[tuple[str, str | None]]) -> None:
        if lower == "a":
            href = self._attr(attrs, "href")
            if href and not href.startswith(("#", "javascript:")):
                self._link_href = href
                self._link_buf = []
            return
        src = self._attr(attrs, "src")
        alt = self._attr(attrs, "alt") or "image"
        if not src:
            return
        if src.startswith("//"):
            src = f"https:{src}"
        self._emit(f"\n\n![{alt}]({src})\n\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "noscript", "svg", "iframe", "nav", "footer", "aside"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if lower == "title":
            self._in_title = True
            return
        if lower in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._pending_heading = lower
            self._heading_buf = []
            self._emit("\n\n")
            return
        if lower == "br":
            self._emit("  \n")
            return
        if lower == "hr":
            self._emit("\n\n---\n\n")
            return
        if lower == "p":
            self._emit("\n\n")
            return
        if lower == "blockquote":
            self._emit("\n\n> ")
            return
        if lower in {"ul", "ol"}:
            self._list_stack.append(lower)
            self._emit("\n")
            return
        if lower == "li":
            marker = "1. " if self._list_stack and self._list_stack[-1] == "ol" else "- "
            self._emit("\n" + marker)
            return
        if lower == "pre":
            self._in_pre = True
            self._code_buf = []
            return
        if lower == "code":
            self._start_code(attrs)
            return
        if lower in {"a", "img"}:
            self._start_link_or_img(lower, attrs)
            return
        if lower in {"strong", "b"}:
            self._emit("**")
            return
        if lower in {"em", "i"}:
            self._emit("*")

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "noscript", "svg", "iframe", "nav", "footer", "aside"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if lower == "title":
            self._in_title = False
            return
        if lower in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._pending_heading == lower:
            level = int(lower[1])
            if text := "".join(self._heading_buf).strip():
                self._emit("#" * level + " " + text + "\n\n")
            self._pending_heading = None
            self._heading_buf = []
            return
        if lower == "p":
            self._emit("\n\n")
            return
        if lower in {"ul", "ol"}:
            if self._list_stack:
                self._list_stack.pop()
            self._emit("\n")
            return
        if lower == "pre":
            body = "".join(self._code_buf).rstrip("\n")
            lang = self._code_lang
            self._emit(f"\n\n```{lang}\n{body}\n```\n\n")
            self._in_pre = False
            self._in_code = False
            self._code_lang = ""
            self._code_buf = []
            return
        if lower == "code":
            if self._in_pre:
                return
            if self._in_code:
                body = "".join(self._code_buf)
                self._emit(f"`{body}`")
                self._in_code = False
                self._code_buf = []
            return
        if lower == "a" and self._link_href is not None:
            label = "".join(self._link_buf).strip() or self._link_href
            self._emit(f"[{label}]({self._link_href})")
            self._link_href = None
            self._link_buf = []
            return
        if lower in {"strong", "b"}:
            self._emit("**")
            return
        if lower in {"em", "i"}:
            self._emit("*")
            return

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            text = data.strip()
            if text and not self.title:
                self.title = text
            return
        if self._pending_heading is not None:
            self._heading_buf.append(data)
            return
        if self._in_pre:
            self._code_buf.append(data)
            return
        if self._in_code:
            self._code_buf.append(data)
            return
        if self._link_href is not None:
            self._link_buf.append(data)
            return
        self._emit(data)

    def markdown(self) -> str:
        raw = "".join(self._parts)
        raw = html.unescape(raw)
        raw = raw.replace("\xa0", " ")
        raw = re.sub(r"[ \t]+\n", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _attr_blob(attrs: str) -> str:
    return attrs.casefold()


def _body_hint_score(attrs: str) -> int:
    blob = _attr_blob(attrs)
    score = 0
    id_match = _ID_ATTR.search(attrs)
    id_value = id_match.group(1).casefold() if id_match else ""
    if id_value in {"post-content-body", "article-body", "content"}:
        score += 500
    class_match = _CLASS_ATTR.search(attrs)
    classes = class_match.group(1).casefold() if class_match else blob
    for hint in _BODY_CLASS_HINTS:
        if hint in classes or hint in blob:
            score += 300
            break
    if "itemprop" in blob and "articlebody" in blob:
        score += 400
    return score


def _is_main_candidate(tag: str, attrs: str) -> bool:
    if _body_hint_score(attrs) > 0:
        return True
    lower = tag.casefold()
    return True if lower == "article" else lower == "main"


def _balanced_fragment(raw: str, start: int, tag: str) -> str | None:
    open_re = re.compile(rf"(?is)<{re.escape(tag)}\b[^>]*>")
    close_re = re.compile(rf"(?is)</{re.escape(tag)}\s*>")
    first = open_re.match(raw, start)
    if first is None:
        return None
    depth = 1
    pos = first.end()
    while pos < len(raw) and depth > 0:
        next_open = open_re.search(raw, pos)
        next_close = close_re.search(raw, pos)
        if next_close is None:
            # Обрезанный HTML: лучше кусок тела до EOF, чем вся страница.
            return raw[start:]
        if next_open is not None and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
            continue
        depth -= 1
        pos = next_close.end()
        if depth == 0:
            return raw[start:pos]
    return raw[start:] if depth > 0 else None


def _score_fragment(tag: str, attrs: str, fragment: str, text_len: int) -> int:
    """Больше = лучше. Штрафуем огромный chrome-<main>, поощряем body-hints."""
    hint = _body_hint_score(attrs)
    html_len = len(fragment)
    if text_len < 80:
        return -1
    density = text_len / max(html_len, 1)
    score = hint * 10 + text_len + int(density * 5_000)
    if tag.casefold() == "main" and hint == 0:
        score -= 50_000  # Habr/и т.п.: <main> тянет сайдбар и комментарии
    if tag.casefold() == "article" and hint == 0:
        score += 2_000
    return score


def extract_main_html(raw: str) -> str:
    """Вырезает HTML тела статьи (не всю страницу с крошками/сайдбаром)."""
    best_html = ""
    best_score = -1
    for match in _OPEN_TAG.finditer(raw):
        tag, attrs = match.group(1), match.group(2)
        if not _is_main_candidate(tag, attrs):
            continue
        fragment = _balanced_fragment(raw, match.start(), tag.casefold())
        if not fragment:
            continue
        _title, text = _html_to_text(fragment)
        score = _score_fragment(tag, attrs, fragment, len(text))
        if score > best_score:
            best_score = score
            best_html = fragment
    return raw if best_score < 0 or len(best_html) < 200 else best_html


def _html_to_text(raw: str) -> tuple[str, str]:
    parser = TextExtractor()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        text = re.sub(r"<[^>]+>", " ", raw)
        return "", text
    return parser.title, parser.text()


def html_to_markdown(raw: str) -> tuple[str, str]:
    parser = MarkdownConverter()
    try:
        parser.feed(raw)
        parser.close()
    except Exception:
        title, text = _html_to_text(raw)
        return title, text
    return parser.title, parser.markdown()


def _normalize_reader_markdown(raw: str) -> tuple[str, str]:
    """Jina/reader: Title + Markdown Content → чистый markdown статьи."""
    title = ""
    if title_match := _READER_TITLE.search(raw):
        title = title_match.group(1).strip()
    mark = _READER_MD_MARK.search(raw)
    body = raw[mark.end() :].lstrip() if mark else raw.strip()
    lines = body.splitlines()
    # Срезать навигацию/баннеры до первого абзаца статьи.
    start = 0
    while start < len(lines):
        line = lines[start].strip()
        if not line:
            start += 1
            continue
        if line.startswith(("#", ">")):
            break
        if len(line) >= 80 and not line.startswith("[") and "http" not in line[:20]:
            break
        if line.startswith(("[", "!", "[](", "* [")) or "Все потоки" in line or line == "Войти":
            start += 1
            continue
        if len(line) < 40:
            start += 1
            continue
        break
    body = "\n".join(lines[start:]).strip()
    if title and not body.lstrip().startswith("#"):
        body = f"# {title}\n\n{body}"
    return title, body


def page_to_plaintext(content_type: str, raw: str) -> tuple[str, str]:
    """Совместимость: plaintext для антибот-проверок."""
    title, markdown = page_to_article_markdown(content_type, raw)
    plain = re.sub(r"[#>*`\-\]\[\(\)!]+", " ", markdown)
    plain = re.sub(r"\s+", " ", plain).strip()
    return title, plain


def page_to_article_markdown(content_type: str, raw: str) -> tuple[str, str]:
    """Полный markdown тела статьи без сжатия и без chrome страницы."""
    ctype = (content_type or "").lower()
    sample = raw[:800].lower()
    looks_md = "markdown" in ctype or "text/plain" in ctype
    looks_html = (
        "html" in ctype
        or "<html" in sample
        or "<!doctype" in sample[:200]
        or "<article" in sample
        or "<div" in sample
    )

    if looks_md and not looks_html:
        return _normalize_reader_markdown(raw)

    if "Markdown Content:" in raw[:4_000]:
        return _normalize_reader_markdown(raw)

    if not looks_html:
        return _normalize_reader_markdown(raw) if raw.strip() else ("", "")

    page_title, _full_plain = _html_to_text(raw)
    main_html = extract_main_html(raw)
    title, markdown = html_to_markdown(main_html)
    if not markdown.strip() and main_html != raw:
        title, markdown = html_to_markdown(raw)
    final_title = (page_title or title or "").strip()
    if final_title and " / " in final_title:
        # «Заголовок / Хабр» → только статья
        final_title = final_title.split(" / ", 1)[0].strip()
    return final_title, markdown


_page_to_plaintext = page_to_plaintext
_page_to_article_markdown = page_to_article_markdown
_TextExtractor = TextExtractor
_extract_main_html = extract_main_html
