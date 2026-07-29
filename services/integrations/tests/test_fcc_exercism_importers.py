from __future__ import annotations

import importlib.util
from pathlib import Path

import httpx
import pytest
from integrations_helpers.loaders import load_integrations_module
from studio_contracts.integration_schemas import ImportReport
from studio_contracts.pack import validate_manifest
from studio_integration_sdk.registry import discover_adapters


@pytest.fixture
def modules_root() -> Path:
    return Path(__file__).resolve().parents[3] / "integration_modules"


def _load_importer(modules_root: Path, platform: str):
    importer_path = modules_root / platform / "importer.py"
    spec = importlib.util.spec_from_file_location(f"{platform}_importer_test", importer_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pack_builder_maps_theory_md_inside_payload() -> None:
    pack_builder = load_integrations_module("app.domain.pack_builder")
    step = pack_builder._coerce_adapter_step(
        {
            "id": "s1",
            "kind": "code",
            "title": "Hello",
            "phase": "practice",
            "fidelity": "partial",
            "payload": {
                "runtime": "python",
                "template": "def solve():\n    pass\n",
                "theory_md": "Write a hello function.",
                "tests": [],
            },
        },
        "practice",
    )
    assert step["payload"]["instructions"] == "Write a hello function."


def test_freecodecamp_fixture_import_builds_valid_manifest(
    modules_root: Path, tmp_path: Path
) -> None:
    pack_builder = load_integrations_module("app.domain.pack_builder")
    adapter = discover_adapters(modules_root)["freecodecamp"]
    pack_raw, report_raw = adapter.import_course(course_id="1")
    normalized = pack_builder.normalized_from_adapter(pack_raw)
    report = ImportReport.model_validate(report_raw)
    manifest = pack_builder.build_manifest(normalized)
    validate_manifest(manifest)
    assert report.total_items == len(normalized.steps)
    assert manifest["source"]["type"] == "freecodecamp"


def test_exercism_fixture_import_builds_valid_manifest(modules_root: Path) -> None:
    pack_builder = load_integrations_module("app.domain.pack_builder")
    adapter = discover_adapters(modules_root)["exercism"]
    pack_raw, report_raw = adapter.import_course(course_id="1")
    normalized = pack_builder.normalized_from_adapter(pack_raw)
    report = ImportReport.model_validate(report_raw)
    validate_manifest(pack_builder.build_manifest(normalized))
    assert "hello-world" in normalized.steps
    assert report.total_items == 1


def test_freecodecamp_maps_page_data_into_code_and_quiz(modules_root: Path) -> None:
    importer = _load_importer(modules_root, "freecodecamp")

    code_step, code_fidelity, _warning = importer._map_challenge(
        step_id="ch-1",
        challenge_id="1",
        title="Declare JavaScript Variables",
        block_slug="basic-javascript",
        superblock="javascript-algorithms-and-data-structures",
        remote={
            "description": ("<section id='description'><p>Variables store values.</p></section>"),
            "instructions": (
                "<section id='instructions'><p>Create <code>myName</code>.</p></section>"
            ),
            "challengeType": 1,
            "helpCategory": "JavaScript",
            "challengeFiles": [{"name": "script", "ext": "js", "contents": "var myName;\n"}],
            "tests": [{"text": "<p>You should declare myName</p>", "testString": "assert(true)"}],
            "questions": [],
            "videoId": "",
            "videoUrl": "",
        },
    )
    assert code_step["kind"] == "code"
    assert code_fidelity == "full"
    assert "myName" in str(code_step["payload"]["template"])
    assert "Variables store values" in str(code_step["payload"]["body_html"])
    assert "You should declare myName" in str(code_step["payload"]["body_html"])
    assert code_step["payload"]["tests"] == []
    assert code_step["payload"]["fcc_tests"]
    assert "assert(true)" in code_step["payload"]["fcc_tests"][0]["test_string"]

    quiz_step, quiz_fidelity, _quiz_warning = importer._map_challenge(
        step_id="ch-2",
        challenge_id="2",
        title="Introduction: Why Program?",
        block_slug="python-for-everybody",
        superblock="python-for-everybody",
        remote={
            "description": "<p>More resources</p>",
            "instructions": "",
            "challengeType": 11,
            "helpCategory": "Python",
            "challengeFiles": [],
            "tests": [],
            "videoId": "3muQV-Im3Z0",
            "questions": [
                {
                    "text": "<p>Who should learn to program?</p>",
                    "answers": [
                        {"answer": "<p>College students.</p>"},
                        {"answer": "<p>Everyone.</p>"},
                    ],
                    "solution": 2,
                }
            ],
        },
    )
    assert quiz_step["kind"] == "quiz"
    assert quiz_fidelity == "full"
    assert quiz_step["payload"]["answer"] == 1
    assert quiz_step["payload"]["choices"] == ["College students.", "Everyone."]
    assert "youtube.com/watch?v=3muQV-Im3Z0" in str(quiz_step["payload"]["video_url"])


def test_exercism_builds_step_from_github_payload(
    modules_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    importer = _load_importer(modules_root, "exercism")

    def _fake_tracks(*_args: object, **_kwargs: object) -> httpx.Response:
        request = httpx.Request("GET", "https://exercism.org/api/v2/tracks")
        return httpx.Response(
            200,
            json={
                "tracks": [
                    {
                        "slug": "python",
                        "title": "Python",
                        "num_exercises": 2,
                        "tags": ["Functional"],
                    },
                ]
            },
            request=request,
        )

    def _fake_exercises(*_args: object, **_kwargs: object) -> httpx.Response:
        request = httpx.Request("GET", "https://exercism.org/api/v2/tracks/python/exercises")
        return httpx.Response(
            200,
            json={
                "exercises": [
                    {
                        "slug": "hello-world",
                        "title": "Hello World",
                        "blurb": "The classical introductory exercise.",
                        "type": "practice",
                    },
                    {
                        "slug": "guidos-gorgeous-lasagna",
                        "title": "Guido's Gorgeous Lasagna",
                        "blurb": "Learn about the basics of Python",
                        "type": "concept",
                    },
                ]
            },
            request=request,
        )

    class _FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def get(self, url: str, *args: object, **kwargs: object) -> httpx.Response:
            if url.endswith("/tracks") and "exercises" not in url:
                return _fake_tracks()
            if url.endswith("/exercises"):
                return _fake_exercises()
            raise AssertionError(f"unexpected url {url}")

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(importer.httpx, "Client", _FakeClient)
    monkeypatch.setattr(
        importer,
        "_enrich_exercises_parallel",
        lambda _track, exercises: {
            "hello-world": {
                "instructions": "# Instructions\n\nReturn Hello, World!",
                "introduction": "",
                "template": "def hello() -> str:\n    return 'Hello, World!'\n",
                "test_source": "def test_hello():\n    assert hello() == 'Hello, World!'\n",
                "solution_file": "hello_world.py",
                "test_file": "hello_world_test.py",
                "source_url": "https://exercism.org/tracks/python/exercises/hello-world",
            },
            "guidos-gorgeous-lasagna": {
                "instructions": "Cook the lasagna.",
                "introduction": "Python basics for cooking.",
                "template": "EXPECTED_BAKE_TIME = 40\n",
                "test_source": "",
                "solution_file": "lasagna.py",
                "test_file": "",
                "source_url": "https://exercism.org/tracks/python/exercises/guidos-gorgeous-lasagna",
            },
        },
    )

    pack, report = importer.import_course(course_id="python")
    assert pack["platform"] == "exercism"
    hello = pack["steps"]["hello-world"]
    assert hello["fidelity"] == "full"
    assert hello["payload"]["solution_file"] == "hello_world.py"
    assert hello["payload"]["test_file"] == "hello_world_test.py"
    assert "Return Hello, World!" in str(hello["payload"]["instructions"])
    assert "Official tests" in str(hello["payload"]["instructions"])
    assert "def hello()" in str(hello["payload"]["template"])
    lasagna_intro = pack["steps"]["guidos-gorgeous-lasagna-intro"]
    assert lasagna_intro["kind"] == "theory"
    assert "Python basics" in str(lasagna_intro["payload"]["instructions"])
    assert report["imported_full"] >= 2

    pack_builder = load_integrations_module("app.domain.pack_builder")
    normalized = pack_builder.normalized_from_adapter(pack)
    assert "instructions" in normalized.steps["hello-world"].payload
    validate_manifest(pack_builder.build_manifest(normalized))


def test_freecodecamp_live_import_uses_page_data(
    modules_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    importer = _load_importer(modules_root, "freecodecamp")

    monkeypatch.setattr(
        importer,
        "_graphql",
        lambda *_args, **_kwargs: {
            "superblock": {
                "name": "JavaScript Algorithms and Data Structures",
                "dashedName": "javascript-algorithms-and-data-structures",
                "blockObjects": [
                    {
                        "name": "Basic JavaScript",
                        "dashedName": "basic-javascript",
                        "challengeOrder": [
                            {
                                "id": "bd7123c9c441eddfaeb4bdef",
                                "title": "Comment Your JavaScript Code",
                            },
                        ],
                    }
                ],
            }
        },
    )
    monkeypatch.setattr(
        importer,
        "_fetch_challenges_parallel",
        lambda _slug, _jobs: {
            "ch-bd7123c9c441eddfaeb4bdef": {
                "description": "<p>Comments are lines of code.</p>",
                "instructions": "<p>Try creating one of each type of comment.</p>",
                "challengeType": 1,
                "helpCategory": "JavaScript",
                "challengeFiles": [{"name": "script", "ext": "js", "contents": "//\n"}],
                "tests": [{"text": "<p>You should create a comment</p>"}],
                "questions": [],
                "videoId": "",
                "videoUrl": "",
            }
        },
    )

    pack, report = importer.import_course(course_id="javascript-algorithms-and-data-structures")
    step = pack["steps"]["ch-bd7123c9c441eddfaeb4bdef"]
    assert step["kind"] == "code"
    assert step["fidelity"] == "full"
    assert "Comments are lines of code" in str(step["payload"]["body_html"])
    assert report["imported_full"] >= 1
