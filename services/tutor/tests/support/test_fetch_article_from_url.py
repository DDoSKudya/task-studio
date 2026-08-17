from __future__ import annotations

import pytest
from studio_contracts.api.studio_schemas import CourseArticleVideo
from tutor_helpers.loaders import load_service_module


@pytest.fixture
def fetch_mod():
    return load_service_module("app.domain.fetch_article_from_url")


def test_validate_rejects_private_hosts(fetch_mod) -> None:
    import sys

    errors = sys.modules["app.domain.errors"]
    with pytest.raises(errors.TutorError):
        fetch_mod.validate_public_http_url("http://127.0.0.1/secret")
    with pytest.raises(errors.TutorError):
        fetch_mod.validate_public_http_url("http://localhost/x")
    with pytest.raises(errors.TutorError):
        fetch_mod.validate_public_http_url("ftp://example.com/a")


def test_validate_allows_public_https(fetch_mod, monkeypatch) -> None:
    import sys

    url_mod = sys.modules["app.domain.fetch_article_from_url.sources.url"]
    monkeypatch.setattr(url_mod, "is_blocked_host", lambda _host: False)
    url = fetch_mod.validate_public_http_url("https://example.com/articles/1")
    assert url.startswith("https://example.com/")


def test_page_to_plaintext_strips_scripts(fetch_mod) -> None:
    html = """
    <html><head><title>Hello</title>
    <script>evil()</script></head>
    <body><article><h1>Hello</h1><p>World body text here.</p></article></body></html>
    """
    title, text = fetch_mod.page_to_plaintext("text/html", html)
    assert title == "Hello"
    assert "World body" in text
    assert "evil" not in text


def test_page_to_plaintext_prefers_article_body(fetch_mod) -> None:
    html = (
        """
    <html><head><title>Docker guide</title></head>
    <body>
      <nav>Home Login Search Menu Items here padding</nav>
      <div class="tm-article-body">
        <h1>Docker vs container</h1>
        <p>"""
        + ("Article paragraph about images and containers. " * 40)
        + """</p>
      </div>
      <aside>Related posts and ads go here with lots of chrome text padding xx</aside>
    </body></html>
    """
    )
    title, text = fetch_mod.page_to_plaintext("text/html", html)
    assert title == "Docker guide"
    assert "Docker vs container" in text
    assert "Article paragraph about images" in text
    assert "Related posts and ads" not in text


def test_page_to_article_markdown_full_habr_body(fetch_mod) -> None:
    from pathlib import Path

    fixture = Path(__file__).parents[1] / "fixtures" / "habr_docker_438796.html"
    raw = fixture.read_text(encoding="utf-8")
    title, markdown = fetch_mod.page_to_article_markdown("text/html", raw)
    assert title.startswith("Изучаем Docker")
    assert len(markdown) > 8_000
    assert "контейнер" in markdown.casefold()
    assert "512K" not in markdown[:2_000]
    assert "Подписаться" not in markdown[:1_500]


def test_page_to_article_markdown_keeps_structure(fetch_mod) -> None:
    html = """
    <html><head><title>Guide</title></head>
    <body>
      <div class="article-formatted-body">
        <h2>Install</h2>
        <p>First paragraph about install steps and docker basics here.</p>
        <pre><code class="language-bash">docker run hello-world</code></pre>
        <p>Second paragraph continues the article with more detail text.</p>
      </div>
    </body></html>
    """
    title, markdown = fetch_mod.page_to_article_markdown("text/html", html)
    assert title == "Guide"
    assert "## Install" in markdown
    assert "```bash" in markdown
    assert "docker run hello-world" in markdown
    assert "First paragraph" in markdown
    assert len(markdown) > 100


def test_extract_prefers_incomplete_body_over_page_chrome(fetch_mod) -> None:

    padding = "<!-- chrome " + ("x" * 8_000) + " -->"
    body = (
        "<p>Введение в Docker и контейнеры. " * 40 + "</p>"
        "<h3>Установка</h3><p>Дальше про install и образы. " * 20 + "</p>"
    )
    html = f"""<!DOCTYPE html><html><body>
    <nav>Все потоки Войти Подписаться Охват за 30 дней</nav>
    {padding}
    <div id="post-content-body">{body}
    """
    title, markdown = fetch_mod.page_to_article_markdown("text/html", html)
    assert "Введение в Docker" in markdown
    assert "Подписаться" not in markdown
    assert "Все потоки" not in markdown


def test_apply_dechrome_removes_exact_ads() -> None:
    from app.domain.fetch_article_from_url.parsing.dechrome import apply_dechrome

    source = (
        "# Docker\n\n"
        "Real article paragraph about containers and images here.\n\n"
        "РЕКЛАМА: Купи VPS со скидкой прямо сейчас!!!\n\n"
        "More teaching content about docker run and volumes.\n"
    )
    cleaned, removed = apply_dechrome(
        source,
        remove_excerpts=["РЕКЛАМА: Купи VPS со скидкой прямо сейчас!!!"],
        title_hint="Docker",
    )
    assert removed > 0
    assert "РЕКЛАМА" not in cleaned
    assert "Real article paragraph" in cleaned
    assert "docker run" in cleaned


def test_apply_dechrome_rejects_over_removal() -> None:
    from app.domain.fetch_article_from_url.parsing.dechrome import apply_dechrome

    source = "Short body with some ads and more text to fill."
    cleaned, removed = apply_dechrome(
        source,
        remove_excerpts=[source],
    )
    assert removed == 0
    assert cleaned == source


def test_looks_like_challenge_html() -> None:
    from app.domain.fetch_article_from_url.sources.challenge import looks_like_challenge_html

    assert looks_like_challenge_html("<html>Just a moment... cf-challenge</html>") is True
    readable = "<html><article><p>" + ("hi " * 40) + "</p></article></html>"
    assert looks_like_challenge_html(readable) is False

    habr_css = (
        "<html><head><style>.grecaptcha-badge{visibility:hidden}</style></head>"
        "<body><article><p>" + ("article body text here. " * 30) + "</p></article></body></html>"
    )
    assert looks_like_challenge_html(habr_css) is False


@pytest.mark.asyncio
async def test_fetch_page_uses_wikipedia_rest_on_direct_403(monkeypatch) -> None:
    from fastapi import status

    page_fetch = load_service_module("app.domain.fetch_article_from_url.sources.page_fetch")

    async def fake_direct(_client, _url):
        raise page_fetch.TutorError(status.HTTP_502_BAD_GATEWAY, "url returned HTTP 403")

    async def fake_wiki(_client, page_url: str):
        assert "wikipedia.org/wiki/" in page_url
        body = (
            "<html><body><p>"
            + ("Photosynthesis converts light energy. " * 20)
            + "</p></body></html>"
        )
        return "text/html", body

    monkeypatch.setattr(page_fetch, "_fetch_direct", fake_direct)
    monkeypatch.setattr(page_fetch, "_fetch_wikipedia_rest", fake_wiki)

    content_type, raw = await page_fetch.fetch_page(
        object(),
        "https://en.wikipedia.org/wiki/Photosynthesis",
    )
    assert "html" in content_type
    assert "Photosynthesis converts light" in raw


def test_wikipedia_rest_url_helper() -> None:
    from app.domain.fetch_article_from_url.sources.wikipedia import wikipedia_rest_html_url

    assert (
        wikipedia_rest_html_url("https://en.wikipedia.org/wiki/DNA")
        == "https://en.wikipedia.org/api/rest_v1/page/html/DNA"
    )
    assert wikipedia_rest_html_url("https://docs.python.org/3/library/os.html") is None


@pytest.mark.asyncio
async def test_fetch_page_falls_back_to_reader(monkeypatch) -> None:
    import sys

    page_fetch = load_service_module("app.domain.fetch_article_from_url.sources.page_fetch")
    url_mod = sys.modules["app.domain.fetch_article_from_url.sources.url"]
    monkeypatch.setattr(url_mod, "is_blocked_host", lambda _host: False)

    async def fake_direct(_client, _url):
        return "text/html", "<html><body>Just a moment... cf-browser-verification</body></html>"

    async def fake_reader(_client, *, reader_base: str, source_url: str):
        assert "jina" in reader_base
        assert source_url.startswith("https://")
        body = "# Hello\n\n" + ("Full article body from reader. " * 40)
        return "text/markdown", body

    monkeypatch.setattr(page_fetch, "_fetch_direct", fake_direct)
    monkeypatch.setattr(page_fetch, "_fetch_via_reader", fake_reader)

    content_type, raw = await page_fetch.fetch_page(
        object(),
        "https://example.com/a",
        reader_base="https://r.jina.ai",
    )
    assert "markdown" in content_type or raw.startswith("# Hello")
    assert "Full article body from reader" in raw


@pytest.mark.asyncio
async def test_fetch_page_keeps_direct_when_readable(monkeypatch) -> None:
    page_fetch = load_service_module("app.domain.fetch_article_from_url.sources.page_fetch")

    async def fake_direct(_client, _url):
        body = "<html><head><title>T</title></head><body><div class='article-formatted-body'><p>"

        body += "Readable article paragraph. " * 80
        body += "</p></div></body></html>"
        return "text/html", body

    async def boom(*_args, **_kwargs):
        raise AssertionError("reader must not run")

    monkeypatch.setattr(page_fetch, "_fetch_direct", fake_direct)
    monkeypatch.setattr(page_fetch, "_fetch_via_reader", boom)

    content_type, raw = await page_fetch.fetch_page(
        object(),
        "https://example.com/a",
        reader_base="https://r.jina.ai",
    )
    assert "html" in content_type
    assert "Readable article paragraph" in raw


@pytest.mark.asyncio
async def test_fetch_page_picks_longer_reader(monkeypatch) -> None:
    page_fetch = load_service_module("app.domain.fetch_article_from_url.sources.page_fetch")

    async def fake_direct(_client, _url):
        thin = "<html><body><div class='article-formatted-body'><p>"
        thin += "Short stub only. " * 8
        thin += "</p></div></body></html>"
        return "text/html", thin

    async def fake_reader(_client, *, reader_base: str, source_url: str):
        body = "# Full\n\n" + ("Longer article body from reader proxy. " * 50)
        return "text/markdown", body

    monkeypatch.setattr(page_fetch, "_fetch_direct", fake_direct)
    monkeypatch.setattr(page_fetch, "_fetch_via_reader", fake_reader)

    _ct, raw = await page_fetch.fetch_page(
        object(),
        "https://example.com/thin",
        reader_base="https://r.jina.ai",
    )
    assert "Longer article body from reader" in raw


@pytest.mark.asyncio
async def test_fetch_article_accepts_short_news(monkeypatch) -> None:

    import uuid
    from types import SimpleNamespace

    from studio_contracts.api.studio_schemas import FetchArticleFromUrlRequest

    service = load_service_module("app.domain.fetch_article_from_url.sources.service")
    body = (
        "Короткая новость про релиз Docker Desktop и новые флаги CLI. "
        "Текст намеренно короче старого порога в пятьсот символов."
    )
    html = (
        "<html><head><title>News</title></head>"
        f"<body><article><p>{body}</p></article></body></html>"
    )

    async def fake_fetch(_client, url, *, reader_base=None):
        return "text/html", html

    async def no_settings(*_args, **_kwargs):
        from app.domain.errors import TutorError
        from fastapi import status

        raise TutorError(status.HTTP_503_SERVICE_UNAVAILABLE, "no settings")

    monkeypatch.setattr(service, "fetch_page", fake_fetch)
    monkeypatch.setattr(service, "validate_public_http_url", lambda u: u.strip())
    monkeypatch.setattr(service, "fetch_user_settings", no_settings)

    config = SimpleNamespace(article_fetch_reader_url="")
    result = await service.fetch_article_from_url(
        object(),
        config,
        user_id=uuid.uuid4(),
        body=FetchArticleFromUrlRequest(url="https://example.com/news"),
    )
    assert "Docker Desktop" in result.content
    assert len(result.content) >= 80


@pytest.mark.asyncio
async def test_fetch_article_survives_auth_connect_error(monkeypatch) -> None:
    import uuid
    from types import SimpleNamespace

    import httpx
    from studio_contracts.api.studio_schemas import FetchArticleFromUrlRequest

    service = load_service_module("app.domain.fetch_article_from_url.sources.service")
    body = "Короткая новость про релиз Docker Desktop и новые флаги CLI. " * 3
    html = (
        "<html><head><title>News</title></head>"
        f"<body><article><p>{body}</p></article></body></html>"
    )

    async def fake_fetch(_client, url, *, reader_base=None):
        return "text/html", html

    async def auth_down(*_args, **_kwargs):
        raise httpx.ConnectError(
            "auth down",
            request=httpx.Request("GET", "http://auth:8001/internal/v1/auth/me"),
        )

    monkeypatch.setattr(service, "fetch_page", fake_fetch)
    monkeypatch.setattr(service, "validate_public_http_url", lambda u: u.strip())
    monkeypatch.setattr(service, "fetch_user_settings", auth_down)

    config = SimpleNamespace(article_fetch_reader_url="")
    result = await service.fetch_article_from_url(
        object(),
        config,
        user_id=uuid.uuid4(),
        body=FetchArticleFromUrlRequest(url="https://example.com/news"),
    )
    assert "Docker Desktop" in result.content


def test_parse_article_json_ok(fetch_mod) -> None:
    raw = '{"title": "T", "content": "' + ("x" * 50) + '"}'
    result = fetch_mod.parse_article_json(
        raw, fallback_title="F", source_url="https://example.com/a"
    )
    assert result.title == "T"
    assert len(result.content) == 50
    assert result.videos == []


def test_extract_video_refs_from_iframe_and_links(fetch_mod) -> None:
    html = """
    <p>See <a href="https://youtu.be/dQw4w9WgXcQ">talk</a></p>
    <iframe src="https://www.youtube.com/embed/abcdefghijk"></iframe>
    <iframe src="https://player.vimeo.com/video/123456789"></iframe>
    """
    videos = fetch_mod.extract_video_refs(html)
    urls = [item.url for item in videos]
    assert "https://www.youtube.com/watch?v=dQw4w9WgXcQ" in urls
    assert "https://www.youtube.com/watch?v=abcdefghijk" in urls
    assert "https://vimeo.com/123456789" in urls
    assert len(urls) == len(set(urls))


def test_plaintext_fallback_builds_markdown(fetch_mod) -> None:
    from app.domain.fetch_article_from_url.plaintext_fallback import plaintext_article_response

    result = plaintext_article_response(
        source_url="https://example.com/a",
        page_title="Hello",
        plaintext="World body text here. " * 8,
        page_videos=[],
    )
    assert result.title == "Hello"
    assert result.content.startswith("# Hello")
    assert "World body" in result.content

    raw = '{"title": "T", "content": "' + ("x" * 50) + ' https://youtu.be/zzzzzzzzzzz"}'
    result = fetch_mod.parse_article_json(
        raw,
        fallback_title="F",
        source_url="https://example.com/a",
        videos=[CourseArticleVideo(url="https://www.youtube.com/watch?v=abcdefghijk")],
    )
    assert result.videos[0].url.endswith("abcdefghijk")
    assert any(video.url.endswith("zzzzzzzzzzz") for video in result.videos)


def test_looks_like_page_chrome_is_site_agnostic() -> None:
    page_fetch = load_service_module("app.domain.fetch_article_from_url.sources.page_fetch")
    ru_chrome = "Все потоки Войти Подписаться Охват за 30 дней " + "x" * 400
    en_chrome = "Sign in Subscribe Cookie policy Privacy policy " + "x" * 400
    article = "Introduction to API design. " * 40
    assert page_fetch._looks_like_page_chrome(ru_chrome) is True
    assert page_fetch._looks_like_page_chrome(en_chrome) is True
    assert page_fetch._looks_like_page_chrome(article) is False


@pytest.mark.asyncio
async def test_fetch_page_reader_when_chrome_markdown(monkeypatch) -> None:

    page_fetch = load_service_module("app.domain.fetch_article_from_url.sources.page_fetch")

    chrome = (
        "<html><body><main><p>Все потоки Войти Подписаться Охват за 30 дней Рейтинг "
        + ("nav pad " * 200)
        + "</p><p>tiny</p></main></body></html>"
    )

    async def fake_direct(_client, _url):
        return "text/html", chrome

    async def fake_reader(_client, *, reader_base: str, source_url: str):
        return "text/markdown", "# Real\n\n" + ("Article from reader about docker. " * 60)

    monkeypatch.setattr(page_fetch, "_fetch_direct", fake_direct)
    monkeypatch.setattr(page_fetch, "_fetch_via_reader", fake_reader)

    _ct, raw = await page_fetch.fetch_page(
        object(),
        "https://example.com/chrome",
        reader_base="https://r.jina.ai",
    )
    assert "Article from reader" in raw


@pytest.mark.asyncio
async def test_fetch_article_is_deterministic_without_llm(monkeypatch) -> None:

    import uuid
    from types import SimpleNamespace

    from studio_contracts.api.studio_schemas import FetchArticleFromUrlRequest

    service = load_service_module("app.domain.fetch_article_from_url.sources.service")
    long_body = "Paragraph about docker images and layers. " * 400
    html = (
        "<html><head><title>Long Docker</title></head>"
        f"<body><article><p>{long_body}</p></article></body></html>"
    )

    async def fake_fetch(_client, url, *, reader_base=None):
        assert url.startswith("https://")
        return "text/html", html

    async def no_settings(*_args, **_kwargs):
        from app.domain.errors import TutorError
        from fastapi import status

        raise TutorError(status.HTTP_503_SERVICE_UNAVAILABLE, "no settings")

    monkeypatch.setattr(service, "fetch_page", fake_fetch)
    monkeypatch.setattr(service, "validate_public_http_url", lambda u: u.strip())
    monkeypatch.setattr(service, "fetch_user_settings", no_settings)

    config = SimpleNamespace(article_fetch_reader_url="https://r.jina.ai")
    result = await service.fetch_article_from_url(
        object(),
        config,
        user_id=uuid.uuid4(),
        body=FetchArticleFromUrlRequest(url="https://example.com/long"),
    )
    assert "docker images" in result.content.casefold()
    assert len(result.content) > 8_000


@pytest.mark.asyncio
async def test_fetch_article_applies_llm_dechrome(monkeypatch) -> None:
    import uuid
    from types import SimpleNamespace

    from studio_contracts.api.studio_schemas import FetchArticleFromUrlRequest
    from studio_contracts.api.tutor_schemas import TutorSettings

    service = load_service_module("app.domain.fetch_article_from_url.sources.service")
    article = (
        "# Title\n\n"
        + ("Useful teaching paragraph about networking. " * 30)
        + "\n\nAD BLOCK BUY NOW CHEAP VPS OFFER\n\n"
        + ("More useful content continues here with details. " * 20)
    )
    html = (
        "<html><head><title>Title</title></head>"
        f"<body><div class='article-formatted-body'><p>{article}</p></div></body></html>"
    )

    async def fake_fetch(_client, url, *, reader_base=None):
        return "text/html", html

    async def fake_settings(*_args, **_kwargs):
        return TutorSettings()

    async def fake_polish(_client, _config, _target, *, source_url, page_title, markdown):
        cleaned = markdown.replace("AD BLOCK BUY NOW CHEAP VPS OFFER", "")
        return page_title, cleaned

    monkeypatch.setattr(service, "fetch_page", fake_fetch)
    monkeypatch.setattr(service, "validate_public_http_url", lambda u: u.strip())
    monkeypatch.setattr(service, "fetch_user_settings", fake_settings)
    monkeypatch.setattr(
        service,
        "resolve_llm_target",
        lambda *_a, **_k: SimpleNamespace(model="x", base_url="http://x"),
    )
    monkeypatch.setattr(service, "polish_article_markdown", fake_polish)

    config = SimpleNamespace(article_fetch_reader_url="")
    result = await service.fetch_article_from_url(
        object(),
        config,
        user_id=uuid.uuid4(),
        body=FetchArticleFromUrlRequest(url="https://example.com/a"),
    )
    assert "AD BLOCK" not in result.content
    assert "Useful teaching paragraph" in result.content


def test_extract_http_urls_from_multiline_paste(fetch_mod, monkeypatch) -> None:
    import sys

    url_mod = sys.modules["app.domain.fetch_article_from_url.sources.url"]
    monkeypatch.setattr(url_mod, "is_blocked_host", lambda _host: False)
    urls = fetch_mod.extract_http_urls(
        "https://example.com/a\n"
        "see https://example.com/b,\n"
        "https://example.com/a\n"
        "not-a-url\n"
        "ftp://ignore.example/x"
    )
    assert urls == ["https://example.com/a", "https://example.com/b"]


def test_extract_http_urls_accepts_list_separators(fetch_mod, monkeypatch) -> None:
    import sys

    url_mod = sys.modules["app.domain.fetch_article_from_url.sources.url"]
    monkeypatch.setattr(url_mod, "is_blocked_host", lambda _host: False)
    urls = fetch_mod.extract_http_urls(
        "https://example.com/a, https://example.com/b;https://example.com/c|https://example.com/d"
    )
    assert urls == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
        "https://example.com/d",
    ]


@pytest.mark.asyncio
async def test_fetch_articles_from_urls_continues_after_error(monkeypatch) -> None:
    import uuid
    from types import SimpleNamespace

    from studio_contracts.api.studio_schemas import (
        FetchArticleFromUrlResponse,
        FetchArticlesFromUrlsRequest,
    )

    service = load_service_module("app.domain.fetch_article_from_url.sources.service")
    errors = __import__("sys").modules["app.domain.errors"]

    async def fake_one(_client, _config, *, user_id, body):
        if "fail" in body.url:
            raise errors.TutorError(422, "boom")
        return FetchArticleFromUrlResponse(
            title="T",
            content="body " * 20,
            source_url=body.url,
            videos=[],
        )

    monkeypatch.setattr(service, "fetch_article_from_url", fake_one)
    url_mod = __import__("sys").modules["app.domain.fetch_article_from_url.sources.url"]
    monkeypatch.setattr(url_mod, "is_blocked_host", lambda _host: False)

    result = await service.fetch_articles_from_urls(
        object(),
        SimpleNamespace(article_fetch_reader_url=""),
        user_id=uuid.uuid4(),
        body=FetchArticlesFromUrlsRequest(
            urls=["https://example.com/ok", "https://example.com/fail"],
        ),
    )
    assert result.total == 2
    assert result.ok_count == 1
    assert result.error_count == 1
    assert result.results[0].ok is True
    assert result.results[1].ok is False
    assert result.results[1].error


@pytest.mark.asyncio
async def test_ollama_polish_analyzes_only_first_window(monkeypatch) -> None:
    from types import SimpleNamespace

    from app.domain.llm import LlmTarget

    clean = load_service_module("app.domain.fetch_article_from_url.parsing.clean_llm")
    calls: list[int] = []

    async def fake_analyze(*_args, window_index: int, window_total: int, **_kwargs):
        calls.append(window_index)
        return "", [f"ad-{window_index}"]

    monkeypatch.setattr(clean, "_analyze_window", fake_analyze)
    monkeypatch.setattr(clean, "is_ollama_target", lambda *_a, **_k: True)
    monkeypatch.setattr(
        clean,
        "apply_dechrome",
        lambda markdown, *, remove_excerpts, title_hint: (markdown, 1),
    )

    long_md = "Paragraph about FastAPI routing and dependency injection. " * 200
    assert len(clean._windows(long_md)) > 1

    title, body = await clean.polish_article_markdown(
        object(),
        SimpleNamespace(ollama_url="http://ollama:11434"),
        LlmTarget("http://ollama:11434/v1", None, "qwen2.5:7b"),
        source_url="https://example.com/a",
        page_title="T",
        markdown=long_md,
    )
    assert title == "T"
    assert body
    assert calls == [1]
