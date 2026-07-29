from __future__ import annotations

from tutor_helpers.loaders import load_service_module


def test_extract_json_object_strips_fence_and_trailing_comma() -> None:
    repair = load_service_module("app.domain.json_repair")
    raw = """```json
{"title": "T", "ok": true, }
```"""
    parsed = repair.extract_json_object(raw)
    assert parsed is not None
    assert parsed["title"] == "T"
    assert parsed["ok"] is True


def test_extract_json_object_rejects_non_object() -> None:
    repair = load_service_module("app.domain.json_repair")
    assert repair.extract_json_object("[1, 2, 3]") is None
    assert repair.extract_json_object("not json") is None


def test_extract_json_object_takes_first_balanced_object() -> None:
    repair = load_service_module("app.domain.json_repair")
    raw = 'Here is the plan:\n{"pack_id": "x", "chapters": [{"id": "a"}]}\nThanks!'
    parsed = repair.extract_json_object(raw)
    assert parsed is not None
    assert parsed["pack_id"] == "x"
    assert parsed["chapters"][0]["id"] == "a"


def test_extract_json_object_normalizes_smart_quotes() -> None:
    repair = load_service_module("app.domain.json_repair")
    raw = "{“title”: “Course”, “locale”: “ru”}"
    parsed = repair.extract_json_object(raw)
    assert parsed is not None
    assert parsed["title"] == "Course"
    assert parsed["locale"] == "ru"


def test_extract_json_object_salvages_truncated_theory_payload() -> None:
    repair = load_service_module("app.domain.json_repair")
    raw = (
        '{"id": "ch-sync-with-oltp", "kind": "theory", '
        '"title": "Синхронизация с основной БД", '
        '"content": "## Почему Elasticsearch не может быть единственн'
    )
    parsed = repair.extract_json_object(raw)
    assert parsed is not None
    assert parsed["id"] == "ch-sync-with-oltp"
    assert parsed["kind"] == "theory"
    assert "Elasticsearch" in str(parsed["content"])
