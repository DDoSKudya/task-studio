from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from types import ModuleType

import httpx
import pytest
from studio_contracts.api.integration_schemas import ImportReport
from studio_contracts.packs.pack import validate_manifest
from studio_integration_sdk.registry import discover_adapters


def _load_integrations_module(module_name: str) -> ModuleType:
    loaders_path = Path(__file__).resolve().parent / "integrations_helpers" / "loaders.py"
    spec = importlib.util.spec_from_file_location("stepik_pipeline_loaders", loaders_path)
    assert spec is not None and spec.loader is not None
    loaders = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaders)
    return loaders.load_integrations_module(module_name)


@pytest.fixture
def modules_root() -> Path:
    return Path(__file__).resolve().parents[3] / "integration_modules"


def test_discover_all_platform_adapters(modules_root: Path) -> None:
    adapters = discover_adapters(modules_root)
    assert set(adapters) == {"stepik", "exercism", "freecodecamp"}


def test_stepik_fixture_import_builds_valid_manifest(modules_root: Path, tmp_path: Path) -> None:
    pack_builder = _load_integrations_module("app.domain.pack.builder")
    adapter = discover_adapters(modules_root)["stepik"]
    pack_raw, report_raw = adapter.import_course(course_id="123")
    normalized = pack_builder.normalized_from_adapter(pack_raw)
    report = ImportReport.model_validate(report_raw)

    manifest = pack_builder.build_manifest(normalized)
    validate_manifest(manifest)

    built = pack_builder.write_pack_to_disk(
        normalized,
        packs_root=tmp_path,
        user_id=uuid.uuid4(),
    )
    assert (built.disk_path / "manifest.json").is_file()
    assert (built.disk_path / "videos" / "intro.mp4").is_file()
    assert report.total_items == len(normalized.steps)
    assert report.fidelity_percent == 0.0
    assert pack_builder.summarize_report(report).fidelity_percent == 87.5
    assert manifest["source"] == {"type": "stepik", "course_id": "123"}


def test_stepik_search_remote_returns_empty_when_offline(
    modules_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib.util

    importer_path = modules_root / "stepik" / "importer.py"
    spec = importlib.util.spec_from_file_location("stepik_importer_test", importer_path)
    assert spec is not None and spec.loader is not None
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)

    def _offline(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise httpx.HTTPError("offline")

    monkeypatch.setattr(importer, "_api_get", _offline)
    hits = importer.search_remote(query="Python")
    assert hits == []


def test_stepik_search_keeps_enrolled_and_marks_public(
    modules_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib.util

    importer_path = modules_root / "stepik" / "importer.py"
    spec = importlib.util.spec_from_file_location("stepik_importer_enroll", importer_path)
    assert spec is not None and spec.loader is not None
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)

    monkeypatch.setattr(
        importer,
        "list_catalog",
        lambda **_kwargs: [
            {
                "id": "10",
                "external_id": "10",
                "platform": "stepik",
                "title": "Python Basics",
                "description": "intro",
                "author": "",
                "language": "ru",
                "tags": [],
                "enrolled": True,
                "is_paid": False,
            }
        ],
    )
    monkeypatch.setattr(importer, "_maybe_access_token", lambda **_kwargs: "token")

    def _fake_get(_client: object, path: str, **kwargs: object) -> dict[str, object]:
        assert path == "courses"
        return {
            "courses": [
                {
                    "id": 10,
                    "title": "Python Basics",
                    "summary": "intro",
                    "is_paid": False,
                },
                {
                    "id": 99,
                    "title": "Python Pro Paid",
                    "summary": "advanced",
                    "is_paid": True,
                },
            ]
        }

    monkeypatch.setattr(importer, "_api_get", _fake_get)
    hits = importer.search_remote(query="Python", username="u", password="p", client_id="c")
    by_id = {str(item["external_id"]): item for item in hits}
    assert by_id["10"]["enrolled"] is True
    assert by_id["99"]["enrolled"] is False
    assert by_id["99"]["is_paid"] is True


def test_stepik_enroll_course_posts_enrollment(modules_root: Path, monkeypatch) -> None:
    import importlib.util

    importer_path = modules_root / "stepik" / "importer.py"
    spec = importlib.util.spec_from_file_location("stepik_importer_enroll_api", importer_path)
    assert spec is not None and spec.loader is not None
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)

    monkeypatch.setattr(importer, "_maybe_access_token", lambda **_kwargs: "token")
    monkeypatch.setattr(importer, "_ensure_stepik_csrf", lambda _client: None)
    monkeypatch.setattr(importer, "_enrollment_exists", lambda *_args, **_kwargs: False)

    posted: dict[str, object] = {}

    def _fake_post(_client: object, path: str, **kwargs: object) -> dict[str, object]:
        posted["path"] = path
        posted["body"] = kwargs.get("body")
        return {"enrollments": [{"id": 1, "course": 42}]}

    monkeypatch.setattr(importer, "_api_post", _fake_post)
    result = importer.enroll_course(course_id="42", username="u", password="p", client_id="c")
    assert result == {"enrolled": True, "already": False}
    assert posted["path"] == "enrollments"
    assert posted["body"] == {"enrollment": {"course": 42}}


def test_stepik_enroll_course_already_enrolled(modules_root: Path, monkeypatch) -> None:
    import importlib.util

    importer_path = modules_root / "stepik" / "importer.py"
    spec = importlib.util.spec_from_file_location("stepik_importer_enroll_already", importer_path)
    assert spec is not None and spec.loader is not None
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)

    monkeypatch.setattr(importer, "_maybe_access_token", lambda **_kwargs: "token")
    monkeypatch.setattr(importer, "_enrollment_exists", lambda *_args, **_kwargs: True)

    def _fail_post(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("should not post when already enrolled")

    monkeypatch.setattr(importer, "_api_post", _fail_post)
    result = importer.enroll_course(course_id="42", username="u", password="p", client_id="c")
    assert result == {"enrolled": True, "already": True}


def test_stepik_manifest_uses_password_auth(modules_root: Path) -> None:
    adapter = discover_adapters(modules_root)["stepik"]
    assert adapter.info.auth is not None
    assert adapter.info.auth.type == "password"
    assert adapter.info.auth.settings_fields == [
        "username",
        "password",
    ]
    assert adapter.info.auth.optional_settings_fields == [
        "client_id",
        "client_secret",
    ]
    assert adapter.enroll is not None


def test_stepik_map_step_source_keeps_full_text_and_choice_options(
    modules_root: Path,
) -> None:
    import importlib.util

    importer_path = modules_root / "stepik" / "importer.py"
    spec = importlib.util.spec_from_file_location("stepik_importer_map", importer_path)
    assert spec is not None and spec.loader is not None
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)

    long_html = (
        "<p>"
        + ("слово " * 120)
        + '</p><p><img src="/media/images/demo.png" alt="demo"></p>'
        + "<pre><code>print(1)\nprint(2)</code></pre>"
    )
    theory, fidelity, warning = importer._map_step_source(
        {"title": "Theory", "block": {"name": "text", "text": long_html}},
        step_id="s1",
    )
    assert fidelity == "full"
    assert warning is None
    instructions = str(theory["payload"]["instructions"])
    assert len(instructions) > 400
    assert "слово" in instructions
    assert "print(1)" in str(theory["payload"]["body_html"])
    assert theory["payload"]["images"] == ["https://stepik.org/media/images/demo.png"]
    assert theory["payload"]["code_examples"][0]["code"] == "print(1)\nprint(2)"
    assert importer._looks_truncated("x" * 400)
    assert not importer._looks_truncated("Short complete sentence.")
    assert (
        importer._step_title(
            {"title": "text", "block": {"name": "text", "text": "<p>Hi</p>"}},
            block_name="text",
            fallback_title="Урок 1. Введение",
            step_id="s1",
        )
        == "Урок 1. Введение"
    )

    video, video_fidelity, _video_warning = importer._map_step_source(
        {
            "title": "Clip",
            "block": {
                "name": "video",
                "text": "<p>Watch</p>",
                "video": {
                    "urls": [
                        {"quality": "360", "url": "https://cdn.example/a.mp4"},
                        {"quality": "720", "url": "https://cdn.example/b.mp4"},
                    ],
                    "thumbnail": "https://cdn.example/poster.jpg",
                },
            },
        },
        step_id="s2",
    )
    assert video_fidelity == "full"
    assert video["payload"]["video_url"] == "https://cdn.example/b.mp4"
    assert video["payload"]["poster_url"] == "https://cdn.example/poster.jpg"

    code, code_fidelity, code_warning = importer._map_step_source(
        {
            "title": "Task",
            "block": {
                "name": "code",
                "text": "<p>Implement <code>add</code></p>",
                "source": {
                    "templates_data": {
                        "python3": "def add(a, b):\n    pass\n",
                        "java": "class Main {}",
                    }
                },
            },
        },
        step_id="s2b",
    )
    assert code_fidelity == "partial"
    assert code_warning is not None
    assert code["payload"]["runtime"] == "python"
    assert "def add" in str(code["payload"]["template"])
    assert "body_html" in code["payload"]

    quiz, quiz_fidelity, quiz_warning = importer._map_step_source(
        {
            "title": "Q",
            "block": {
                "name": "choice",
                "text": "<p>Pick one</p>",
                "source": {
                    "options": [
                        {"text": "<b>A</b>", "is_correct": False},
                        {"text": "B", "is_correct": True},
                        {"text": "C", "is_correct": False},
                    ]
                },
            },
        },
        step_id="s3",
    )
    assert quiz_fidelity == "full"
    assert quiz_warning is None
    assert quiz["phase"] == "assess"
    assert quiz["payload"]["choices"] == ["A", "B", "C"]
    assert quiz["payload"]["answer"] == 1

    quiz_dataset, quiz_dataset_fidelity, quiz_dataset_warning = importer._map_step_source(
        {
            "title": "Q2",
            "block": {
                "name": "choice",
                "text": "<p>Pick one</p>",
                "options": {"is_multiple_choice": False},
                "dataset": {"is_multiple_choice": False, "options": ["One", "Two"]},
            },
        },
        step_id="s4",
    )
    assert quiz_dataset_fidelity == "partial"
    assert quiz_dataset_warning is not None
    assert quiz_dataset["phase"] == "assess"
    assert quiz_dataset["payload"]["choices"] == ["One", "Two"]
    assert "answer" not in quiz_dataset["payload"]


def test_stepik_hydrates_choice_options_from_attempts(
    modules_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib.util

    importer_path = modules_root / "stepik" / "importer.py"
    spec = importlib.util.spec_from_file_location("stepik_importer_attempts", importer_path)
    assert spec is not None and spec.loader is not None
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)

    steps = {
        "10": {
            "id": 10,
            "block": {
                "name": "choice",
                "text": "<p>Q</p>",
                "options": {"is_multiple_choice": False},
            },
        },
        "11": {
            "id": 11,
            "block": {"name": "text", "text": "<p>Theory</p>"},
        },
    }

    monkeypatch.setattr(importer, "_ensure_stepik_csrf", lambda _client: None)

    def _fake_dataset(_client: object, step_id: str, *, token: str | None = None) -> dict:
        assert step_id == "10"
        assert token is None
        return {"is_multiple_choice": False, "options": ["Alpha", "Beta", "Gamma"]}

    monkeypatch.setattr(importer, "_fetch_attempt_dataset", _fake_dataset)
    importer._hydrate_choice_datasets(object(), steps, token=None)
    assert steps["10"]["block"]["dataset"]["options"] == ["Alpha", "Beta", "Gamma"]
    assert "dataset" not in steps["11"]["block"]

    built, fidelity, warning = importer._map_step_source(
        steps["10"],
        step_id="step-10",
    )
    assert fidelity == "partial"
    assert warning is not None
    assert built["phase"] == "assess"
    assert built["payload"]["choices"] == ["Alpha", "Beta", "Gamma"]


def test_stepik_classify_keeps_phase_and_kind_aligned(modules_root: Path) -> None:
    import importlib.util

    importer_path = modules_root / "stepik" / "importer.py"
    spec = importlib.util.spec_from_file_location("stepik_importer_phase", importer_path)
    assert spec is not None and spec.loader is not None
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)

    long_code_like = (
        "<p>Задание: напишите код</p><pre><code>"
        + ("def solve():\n    return 1\n" * 80)
        + "</code></pre>"
    )
    source = {"title": "Task 1", "block": {"name": "text", "text": long_code_like}}
    phase, block_name = importer._classify_stepik_source(source)
    assert block_name == "text"
    assert phase == "practice"
    built, fidelity, _warning = importer._map_step_source(source, step_id="step-code-like")
    assert fidelity == "partial"
    assert built["kind"] == "code"
    assert built["phase"] == "practice"
    assert built["phase"] == phase

    quiz_phase, _ = importer._classify_stepik_source(
        {"title": "Quiz", "block": {"name": "choice", "text": "<p>Q</p>"}}
    )
    assert quiz_phase == "assess"


def test_stepik_fixture_maps_quiz_to_assess(modules_root: Path) -> None:
    adapter = discover_adapters(modules_root)["stepik"]
    pack_raw, report_raw = adapter.import_course(course_id="123")
    assert isinstance(pack_raw, dict)
    assert isinstance(report_raw, dict)
    topics = pack_raw["topics"]
    assert isinstance(topics, list) and topics
    topic = topics[0]
    assert isinstance(topic, dict)
    assess = topic["assess"]
    assert isinstance(assess, list)
    assert "quiz-types" in assess
    steps = pack_raw["steps"]
    assert isinstance(steps, dict)
    quiz = steps["quiz-types"]
    assert isinstance(quiz, dict)
    assert quiz["phase"] == "assess"
    assert report_raw.get("truncated") is not True


def test_stepik_live_truncation_marks_report_truncated(
    modules_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib.util

    importer_path = modules_root / "stepik" / "importer.py"
    spec = importlib.util.spec_from_file_location("stepik_importer_trunc", importer_path)
    assert spec is not None and spec.loader is not None
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)

    monkeypatch.setattr(importer, "_MAX_STEPS", 2)

    class _FakeClient:
        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    monkeypatch.setattr(importer.httpx, "Client", lambda **_kwargs: _FakeClient())

    def _fake_api_get(_client: object, path: str, **_kwargs: object) -> dict[str, object]:
        if path.startswith("courses/"):
            return {"courses": [{"id": 1, "title": "Big", "sections": [1]}]}
        raise AssertionError(path)

    monkeypatch.setattr(importer, "_api_get", _fake_api_get)

    def _fake_fetch_resources(
        _client: object,
        resource: str,
        _ids: list[str],
        **_kwargs: object,
    ) -> dict[str, dict[str, object]]:
        if resource == "sections":
            return {"1": {"id": 1, "title": "S1", "units": [1]}}
        if resource == "units":
            return {"1": {"id": 1, "lesson": 1}}
        if resource == "lessons":
            return {"1": {"id": 1, "title": "L1", "steps": [1, 2, 3]}}
        return {}

    monkeypatch.setattr(importer, "_fetch_resources", _fake_fetch_resources)
    monkeypatch.setattr(
        importer,
        "_fetch_step_sources",
        lambda _client, step_ids, **_kwargs: [
            {
                "id": int(sid),
                "title": f"T{sid}",
                "block": {"name": "text", "text": f"<p>{sid}</p>"},
            }
            for sid in step_ids
        ],
    )

    pack, report = importer._import_live("1", token="token")
    assert report["truncated"] is True
    assert report["skipped"] == 1
    assert len(pack["steps"]) == 2
    assert any("partial" in item["reason"] for item in report["warnings"])


def test_stepik_live_puts_choice_into_topic_assess(
    modules_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib.util

    importer_path = modules_root / "stepik" / "importer.py"
    spec = importlib.util.spec_from_file_location("stepik_importer_assess", importer_path)
    assert spec is not None and spec.loader is not None
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)

    class _FakeClient:
        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

    monkeypatch.setattr(importer.httpx, "Client", lambda **_kwargs: _FakeClient())

    def _fake_api_get(_client: object, path: str, **_kwargs: object) -> dict[str, object]:
        if path.startswith("courses/"):
            return {"courses": [{"id": 1, "title": "Quiz course", "sections": [1]}]}
        raise AssertionError(path)

    monkeypatch.setattr(importer, "_api_get", _fake_api_get)

    def _fake_fetch_resources(
        _client: object,
        resource: str,
        _ids: list[str],
        **_kwargs: object,
    ) -> dict[str, dict[str, object]]:
        if resource == "sections":
            return {"1": {"id": 1, "title": "S1", "units": [1]}}
        if resource == "units":
            return {"1": {"id": 1, "lesson": 1}}
        if resource == "lessons":
            return {"1": {"id": 1, "title": "L1", "steps": [10, 20, 30]}}
        return {}

    monkeypatch.setattr(importer, "_fetch_resources", _fake_fetch_resources)

    sources = {
        "10": {
            "id": 10,
            "title": "Theory",
            "block": {"name": "text", "text": "<p>Read me</p>"},
        },
        "20": {
            "id": 20,
            "title": "Code",
            "block": {
                "name": "code",
                "text": "<p>Implement</p>",
                "source": {"templates_data": {"python3": "def f():\n    pass\n"}},
            },
        },
        "30": {
            "id": 30,
            "title": "Quiz",
            "block": {
                "name": "choice",
                "text": "<p>Pick</p>",
                "source": {
                    "options": [
                        {"text": "A", "is_correct": True},
                        {"text": "B", "is_correct": False},
                    ]
                },
            },
        },
    }
    monkeypatch.setattr(
        importer,
        "_fetch_step_sources",
        lambda _client, step_ids, **_kwargs: [sources[sid] for sid in step_ids],
    )

    pack, report = importer._import_live("1", token="token")
    topic = pack["topics"][0]
    assert topic["study"] == ["step-10"]
    assert topic["practice"] == ["step-20"]
    assert topic["assess"] == ["step-30"]
    assert pack["steps"]["step-30"]["phase"] == "assess"
    assert pack["steps"]["step-20"]["phase"] == "practice"
    assert pack["steps"]["step-10"]["phase"] == "study"
    assert report["truncated"] is False


def test_import_pipeline_marks_truncated_job_partial() -> None:
    report = ImportReport.model_validate(
        {
            "total_items": 2,
            "imported_full": 2,
            "imported_partial": 0,
            "skipped": 1,
            "warnings": [{"step": "course", "reason": "import status is partial"}],
            "truncated": True,
        }
    )
    status = "partial" if report.truncated else "done"
    assert status == "partial"
    assert report.truncated is True
