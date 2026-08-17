from __future__ import annotations

import httpx
import pytest
from tutor_helpers.loaders import load_service_module

_PATHLIB = "https://docs.python.org/3/library/pathlib.html"
_HTML = (
    "<html><body><article><p>"
    "Path.mkdir creates a directory. parents=True creates missing parents."
    "</p></article></body></html>"
)


def _glossary():
    return load_service_module(
        "app.domain.course_from_article.local_course.integrations.web_glossary"
    )


def _thin_chapter() -> dict[str, str]:
    return {"title": "pathlib Path", "source_excerpt": "short"}


def _sources() -> list[dict[str, object]]:
    return [{"title": "pathlib", "content": f"See {_PATHLIB} for Path."}]


def _patch_lookup_sources(glossary, monkeypatch: pytest.MonkeyPatch, url: str = _PATHLIB) -> None:
    monkeypatch.setattr(glossary, "extract_http_urls", lambda *_chunks: [url])
    monkeypatch.setattr(glossary, "url_is_allowed", lambda candidate, _allow: candidate == url)


def test_web_glossary_default_off_even_on_gpu() -> None:
    policy = load_service_module("app.domain.course_from_article.local_course.policy.policy")
    gpu = policy.local_course_policy_for(profile="gpu-balanced", model="qwen2.5:7b")
    cpu = policy.local_course_policy_for(profile="cpu-light", model="qwen2.5:7b")
    assert gpu.web_glossary is False
    assert cpu.web_glossary is False
    on = policy.local_course_policy_for(
        profile="cpu-light",
        model="qwen2.5:7b",
        web_glossary=True,
    )
    assert on.web_glossary is True
    blocked = policy.local_course_policy_for(
        profile="gpu-balanced",
        model="qwen2.5:1.5b",
        web_glossary=True,
    )
    assert blocked.web_glossary is False


def test_empty_allowlist_env_falls_back_to_default() -> None:
    glossary = _glossary()
    assert glossary.DEFAULT_WEB_ALLOWLIST == ()
    assert glossary.parse_host_allowlist("") == ()
    assert glossary.parse_host_allowlist(" docs.python.org , vuejs.org ") == (
        "docs.python.org",
        "vuejs.org",
    )


def test_allowlist_rejects_unknown_host(monkeypatch: pytest.MonkeyPatch) -> None:
    glossary = _glossary()
    monkeypatch.setattr(glossary, "validate_public_http_url", lambda url: url)
    allowlist = ("docs.python.org",)
    assert glossary.url_is_allowed(_PATHLIB, allowlist)
    assert not glossary.url_is_allowed("https://evil.example/steal", allowlist)


def test_localhost_blocked_even_when_allowlisted() -> None:
    glossary = _glossary()
    assert not glossary.url_is_allowed(
        "http://127.0.0.1/secret",
        ("127.0.0.1", "localhost"),
    )


def test_term_needs_glossary_on_thin_excerpt() -> None:
    glossary = _glossary()
    assert glossary.term_needs_glossary("pathlib Path mkdir", "short") is True
    rich = (
        "pathlib Path.mkdir creates a directory. parents=True creates missing parents. "
        "exist_ok=True ignores the error when the folder already exists. "
        "Use Path to join parts instead of os.path.join."
    )
    assert glossary.term_needs_glossary("pathlib Path mkdir", rich) is False


def test_snippet_fits_source_drops_unrelated_when_excerpt_is_rich() -> None:
    glossary = _glossary()
    excerpt = "pathlib Path.mkdir creates directories with parents=True and exist_ok. " * 4
    assert glossary.snippet_fits_source("Path.mkdir creates missing parents", excerpt)
    assert not glossary.snippet_fits_source("Redis TTL expires cache keys forever", excerpt)


def test_format_external_note_uses_prefix() -> None:
    glossary = _glossary()
    note = glossary.format_external_note(
        term="Path.mkdir",
        host="docs.python.org",
        snippet="Create a directory. parents=True creates missing parents.",
    )
    assert note.startswith("external:")
    assert "docs.python.org" in note
    merged = glossary.append_external_note("Lesson from the article.", note)
    assert merged.startswith("Lesson from the article.")
    assert "external:" in merged
    assert glossary.append_external_note(merged, note) == merged


def test_pick_url_requires_title_overlap() -> None:
    glossary = _glossary()
    urls = [
        "https://docs.python.org/3/library/json.html",
        "https://docs.python.org/3/library/pathlib.html",
    ]
    chosen = glossary.pick_url_for_chapter("pathlib Path", urls, seen=set())
    assert chosen is not None
    assert "pathlib" in chosen
    assert glossary.pick_url_for_chapter("FastAPI Depends", urls, seen=set()) is None


def test_load_config_web_glossary_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COURSE_WEB_GLOSSARY", raising=False)
    monkeypatch.delenv("COURSE_WEB_ALLOWLIST", raising=False)
    config = load_service_module("app.config").load_config()
    assert config.course_web_glossary is False
    assert config.course_web_allowlist == ()


def test_resolve_llm_target_keeps_installed_probe() -> None:
    llm = load_service_module("app.domain.llm.target")
    config = load_service_module("app.config").load_config()
    target = llm.resolve_llm_target(
        config,
        provider_url=None,
        api_key_encrypted=None,
        model=None,
        installed_models=["qwen2.5:7b"],
    )
    assert target is not None
    assert target.installed_models == ("qwen2.5:7b",)


@pytest.mark.asyncio
async def test_fetch_error_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    glossary = _glossary()
    _patch_lookup_sources(glossary, monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    lookups = glossary.GlossaryLookups(allowlist=("docs.python.org",), remaining=3)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        note = await glossary.lookup_chapter_note(
            client,
            chapter=_thin_chapter(),
            sources=_sources(),
            article="",
            lookups=lookups,
        )
    assert note == ""
    assert lookups.remaining == 2


@pytest.mark.asyncio
async def test_http_500_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    glossary = _glossary()
    _patch_lookup_sources(glossary, monkeypatch)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="nope")

    lookups = glossary.GlossaryLookups(allowlist=("docs.python.org",), remaining=3)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        note = await glossary.lookup_chapter_note(
            client,
            chapter=_thin_chapter(),
            sources=_sources(),
            article="",
            lookups=lookups,
        )
    assert note == ""
    assert lookups.remaining == 2


@pytest.mark.asyncio
async def test_redirect_off_allowlist_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    glossary = _glossary()
    _patch_lookup_sources(glossary, monkeypatch)
    monkeypatch.setattr(
        glossary,
        "url_is_allowed",
        lambda candidate, _allow: candidate.startswith("https://docs.python.org"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if "pathlib" in str(request.url):
            return httpx.Response(302, headers={"location": "https://evil.example/x"})
        return httpx.Response(200, text=_HTML, headers={"content-type": "text/html"})

    lookups = glossary.GlossaryLookups(allowlist=("docs.python.org",), remaining=3)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        note = await glossary.lookup_chapter_note(
            client,
            chapter=_thin_chapter(),
            sources=_sources(),
            article="",
            lookups=lookups,
        )
    assert note == ""


@pytest.mark.asyncio
async def test_lookup_writes_external_note_for_thin_chapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    glossary = _glossary()
    _patch_lookup_sources(glossary, monkeypatch)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_HTML, headers={"content-type": "text/html"})

    lookups = glossary.GlossaryLookups(allowlist=("docs.python.org",), remaining=3)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        note = await glossary.lookup_chapter_note(
            client,
            chapter=_thin_chapter(),
            sources=_sources(),
            article="",
            lookups=lookups,
        )
    assert note.startswith("external:")
    assert "Path.mkdir" in note or "directory" in note.casefold()
    assert "docs.python.org" in note


@pytest.mark.asyncio
async def test_rich_excerpt_skips_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    glossary = _glossary()
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, text=_HTML)

    rich = (
        "pathlib Path.mkdir creates a directory. parents=True creates missing parents. "
        "exist_ok=True ignores the error when the folder already exists. "
        "Use Path to join parts instead of os.path.join."
    )
    lookups = glossary.GlossaryLookups(allowlist=("docs.python.org",), remaining=3)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        note = await glossary.lookup_chapter_note(
            client,
            chapter={"title": "pathlib Path mkdir", "source_excerpt": rich},
            sources=_sources(),
            article="",
            lookups=lookups,
        )
    assert note == ""
    assert calls["n"] == 0
    assert lookups.remaining == 3


@pytest.mark.asyncio
async def test_fetch_budget_stops_after_three_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    glossary = _glossary()
    calls = {"n": 0}

    def extract(*chunks: str) -> list[str]:
        blob = " ".join(chunks)
        for index in range(4):
            marker = f"pathlib-{index}"
            if marker in blob:
                return [f"https://docs.python.org/3/library/{marker}.html"]
        return [_PATHLIB]

    monkeypatch.setattr(glossary, "extract_http_urls", extract)
    monkeypatch.setattr(glossary, "url_is_allowed", lambda _url, _allow: True)

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, text=_HTML, headers={"content-type": "text/html"})

    lookups = glossary.GlossaryLookups(allowlist=("docs.python.org",), remaining=3)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        for index in range(4):
            await glossary.lookup_chapter_note(
                client,
                chapter={"title": f"pathlib-{index} Path", "source_excerpt": "short"},
                sources=[
                    {
                        "title": f"pathlib-{index}",
                        "content": f"https://docs.python.org/3/library/pathlib-{index}.html",
                    }
                ],
                article="",
                lookups=lookups,
            )
    assert calls["n"] == 3
    assert lookups.remaining == 0


def test_apply_role_adapter_reads_installed_models_on_target() -> None:
    runtime = load_service_module("app.domain.course_adapters.runtime")
    registry = load_service_module("app.domain.course_adapters.registry")
    target_mod = load_service_module("app.domain.llm.target")
    quiz_model = "task-studio-course-quiz:latest"
    book = registry.AdapterRegistry.empty().with_entry(
        registry.stamp_shipped(
            role="course-quiz",
            model=quiz_model,
            eval_mean=0.8,
            compiler_mean=0.5,
        )
    )
    missing = target_mod.LlmTarget(
        "http://ollama:11434/v1",
        None,
        "qwen2.5:7b",
        installed_models=("qwen2.5:7b",),
    )
    present = target_mod.LlmTarget(
        "http://ollama:11434/v1",
        None,
        "qwen2.5:7b",
        installed_models=("qwen2.5:7b", quiz_model),
    )
    assert runtime.apply_role_adapter(missing, "course-quiz", registry=book).model == "qwen2.5:7b"
    assert runtime.apply_role_adapter(present, "course-quiz", registry=book).model == quiz_model
