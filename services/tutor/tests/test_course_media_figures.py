from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_extract_image_refs_from_markdown_and_html() -> None:
    images = load_service_module("app.domain.fetch_article_from_url.images")
    chunk = """
    ![Redis topology](https://cdn.example.com/images/redis-arch.png)
    <img src="https://cdn.example.com/media/cli.webp" alt="CLI output" />
    ![logo](https://cdn.example.com/favicon.ico)
    """
    found = images.extract_image_refs(chunk)
    urls = [item.url for item in found]
    assert "https://cdn.example.com/images/redis-arch.png" in urls
    assert "https://cdn.example.com/media/cli.webp" in urls
    assert all("favicon" not in url for url in urls)


def test_filter_theory_images_keeps_allowlisted_only() -> None:
    source = load_service_module("app.domain.course_from_article.source_images")
    md = (
        "Текст.\n\n"
        "![ok](https://cdn.example.com/images/a.png)\n\n"
        "![bad](https://evil.example/x.png)\n\n"
        "Ещё текст."
    )
    cleaned, urls = source.filter_theory_images(
        md,
        allowed_urls={"https://cdn.example.com/images/a.png"},
    )
    assert "cdn.example.com/images/a.png" in cleaned
    assert "evil.example" not in cleaned
    assert urls == ["https://cdn.example.com/images/a.png"]


def test_attach_source_images_prefers_excerpt_figures() -> None:
    source = load_service_module("app.domain.course_from_article.source_images")
    chapters = [
        {
            "id": "ch-1",
            "title": "Secure Redis",
            "source_excerpt": (
                "Bind address.\n\n![bind](https://cdn.example.com/images/bind.png)\n"
            ),
            "purpose": "",
            "source_titles": "",
            "bridge_from_prev": "",
            "assumes_known": "",
            "must_not_reteach": "",
            "learning_objective": "",
            "source_images": "",
        }
    ]
    sources = [
        {
            "title": "Redis guide",
            "content": "x" * 80,
            "images": [
                {"url": "https://cdn.example.com/images/bind.png", "alt": "bind"},
                {"url": "https://cdn.example.com/images/other.png", "alt": "other"},
            ],
        }
    ]
    updated = source.attach_source_images_to_chapters(chapters, sources)
    assert "bind.png" in updated[0]["source_images"]


def test_attach_source_images_does_not_repeat_catalog_across_chapters() -> None:
    source = load_service_module("app.domain.course_from_article.source_images")
    chapters = [
        {
            "id": "ch-1",
            "title": "Introduction",
            "source_excerpt": "Overview of the platform.",
            "purpose": "",
            "source_titles": "",
            "bridge_from_prev": "",
            "assumes_known": "",
            "must_not_reteach": "",
            "learning_objective": "",
            "source_images": "",
        },
        {
            "id": "ch-2",
            "title": "Advanced topics",
            "source_excerpt": "Deeper dive into architecture.",
            "purpose": "",
            "source_titles": "",
            "bridge_from_prev": "",
            "assumes_known": "",
            "must_not_reteach": "",
            "learning_objective": "",
            "source_images": "",
        },
    ]
    sources = [
        {
            "title": "Guide",
            "content": "x" * 80,
            "images": [
                {"url": "https://cdn.example.com/images/shared.png", "alt": "shared diagram"},
            ],
        }
    ]
    updated = source.attach_source_images_to_chapters(chapters, sources)
    assert updated[0]["source_images"] == ""
    assert updated[1]["source_images"] == ""


def test_attach_source_images_uses_catalog_only_when_relevant() -> None:
    source = load_service_module("app.domain.course_from_article.source_images")
    chapters = [
        {
            "id": "ch-redis",
            "title": "Redis replication",
            "source_excerpt": "Primary and replica nodes in Redis replication topology.",
            "purpose": "",
            "source_titles": "",
            "bridge_from_prev": "",
            "assumes_known": "",
            "must_not_reteach": "",
            "learning_objective": "",
            "source_images": "",
        },
        {
            "id": "ch-other",
            "title": "Team rituals",
            "source_excerpt": "Daily standups keep the team aligned on priorities.",
            "purpose": "",
            "source_titles": "",
            "bridge_from_prev": "",
            "assumes_known": "",
            "must_not_reteach": "",
            "learning_objective": "",
            "source_images": "",
        },
    ]
    sources = [
        {
            "title": "Redis guide",
            "content": "x" * 80,
            "images": [
                {
                    "url": "https://cdn.example.com/images/redis-replication.png",
                    "alt": "Redis replication topology",
                },
                {
                    "url": "https://cdn.example.com/images/logging.png",
                    "alt": "logging pipeline",
                },
            ],
        }
    ]
    updated = source.attach_source_images_to_chapters(chapters, sources)
    assert "redis-replication.png" in updated[0]["source_images"]
    assert updated[1]["source_images"] == ""


def test_attach_rejects_generic_tokens_and_offtopic_diagram() -> None:
    source = load_service_module("app.domain.course_from_article.source_images")
    chapters = [
        {
            "id": "ch-why",
            "title": "Почему это удобно?",
            "source_excerpt": "Сравнение на схеме. Docker containers and virtualization overview.",
            "purpose": "",
            "source_titles": "",
            "bridge_from_prev": "",
            "assumes_known": "",
            "must_not_reteach": "",
            "learning_objective": "",
            "source_images": "",
        },
        {
            "id": "ch-myth",
            "title": "Миф про изоляцию",
            "source_excerpt": "Контейнеры делят ядро хостовой ОС.",
            "purpose": "",
            "source_titles": "",
            "bridge_from_prev": "",
            "assumes_known": "",
            "must_not_reteach": "",
            "learning_objective": "",
            "source_images": "",
        },
    ]
    sources = [
        {
            "title": "Containers guide",
            "content": "x" * 80,
            "images": [
                {
                    "url": "https://cdn.example.com/images/vm-vs-docker.png",
                    "alt": "SERVER WITH VIRTUAL MACHINES vs DOCKER CONTAINERS",
                },
            ],
        }
    ]
    updated = source.attach_source_images_to_chapters(chapters, sources)
    assert updated[0]["source_images"] == ""
    assert updated[1]["source_images"] == ""


def test_articles_from_body_collects_images() -> None:
    course = load_service_module("app.domain.course_from_article")
    from studio_contracts.studio_schemas import CourseArticleInput, CourseFromArticleRequest

    body = CourseFromArticleRequest(
        articles=[
            CourseArticleInput(
                title="With figure",
                content=(
                    "Install Redis.\n\n"
                    "![ports](https://cdn.example.com/images/ports.png)\n\n" + ("more text " * 20)
                ),
            )
        ]
    )
    sources = course._articles_from_body(body)
    assert sources[0]["images"]
    assert sources[0]["images"][0]["url"].endswith("ports.png")


def test_assemble_places_video_after_first_theory() -> None:
    course = load_service_module("app.domain.course_from_article")
    manifest = course._assemble_manifest(
        pack_id="demo",
        title="Demo",
        locale="ru",
        runtime="python",
        runtime_version="3.12",
        theory_steps=[
            {"id": "theory-a", "kind": "theory", "title": "A", "content": "a"},
            {"id": "theory-b", "kind": "theory", "title": "B", "content": "b"},
        ],
        video_steps=[
            {
                "id": "video-1",
                "kind": "video",
                "title": "Talk",
                "video_url": "https://www.youtube.com/watch?v=abcdefghijk",
            }
        ],
        quiz_steps=[],
        code_steps=[],
    )
    assert manifest["topics"][0]["phases"]["study"]["steps"] == [
        "theory-a",
        "video-1",
        "theory-b",
    ]
