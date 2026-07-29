from __future__ import annotations

import pytest
from studio_contracts.studio_schemas import CourseArticleVideo
from tutor_helpers.loaders import load_service_module


@pytest.fixture(scope="module")
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

    url_mod = sys.modules["app.domain.fetch_article_from_url.url"]
    monkeypatch.setattr(url_mod, "is_blocked_host", lambda _host: False)
    url = fetch_mod.validate_public_http_url("https://example.com/articles/1")
    assert url.startswith("https://example.com/")


def test_page_to_plaintext_strips_scripts(fetch_mod) -> None:
    html = """
    <html><head><title>Hello</title>
    <script>evil()</script></head>
    <body><article><h1>Hello</h1><p>World body text here.</p></article></body></html>
    """
    title, text = fetch_mod._page_to_plaintext("text/html", html)
    assert title == "Hello"
    assert "World body" in text
    assert "evil" not in text


def test_parse_article_json_ok(fetch_mod) -> None:
    raw = '{"title": "T", "content": "' + ("x" * 50) + '"}'
    result = fetch_mod._parse_article_json(
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
    result = fetch_mod._parse_article_json(
        raw,
        fallback_title="F",
        source_url="https://example.com/a",
        videos=[CourseArticleVideo(url="https://www.youtube.com/watch?v=abcdefghijk")],
    )
    assert result.videos[0].url.endswith("abcdefghijk")
    assert any(video.url.endswith("zzzzzzzzzzz") for video in result.videos)
