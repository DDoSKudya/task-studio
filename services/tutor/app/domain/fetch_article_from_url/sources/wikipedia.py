from __future__ import annotations

from urllib.parse import quote, unquote, urlparse

_WIKI_HOST_SUFFIXES = (".wikipedia.org",)


def wikipedia_rest_html_url(page_url: str) -> str | None:

    parsed = urlparse(page_url)
    host = (parsed.hostname or "").casefold()
    if not host.endswith(_WIKI_HOST_SUFFIXES):
        return None
    marker = "/wiki/"
    if marker not in parsed.path:
        return None
    title = parsed.path.split(marker, 1)[1].strip("/")
    if not title or "/" in title:
        return None
    title = quote(unquote(title), safe=":()_")
    lang = host.split(".", 1)[0]
    if not lang:
        return None
    return f"https://{lang}.wikipedia.org/api/rest_v1/page/html/{title}"
