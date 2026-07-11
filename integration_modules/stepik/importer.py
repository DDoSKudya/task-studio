from __future__ import annotations

import json
from pathlib import Path

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def health() -> dict[str, object]:
    return {"status": "ok", "platform": "stepik"}


def list_catalog(**_ctx: object) -> list[dict[str, object]]:
    return [
        {
            "id": "123",
            "title": "Intro Python",
            "description": "Basics of Python programming",
        }
    ]


def search_remote(*, query: str, **_ctx: object) -> list[dict[str, object]]:
    needle = query.casefold()
    return [
        item
        for item in list_catalog()
        if needle in str(item["title"]).casefold()
        or needle in str(item.get("description", "")).casefold()
    ]


def import_course(*, course_id: str, **_ctx: object) -> tuple[dict[str, object], dict[str, object]]:
    payload = _load_fixture(course_id)
    steps = _fixture_steps(payload)
    pack = {
        "platform": "stepik",
        "external_id": course_id,
        "title": payload["title"],
        "slug": f"stepik-{course_id}",
        "version": payload.get("version", "1.0.0"),
        "locale": payload.get("locale", "en"),
        "topics": payload["topics"],
        "steps": steps,
        "course_assess": payload.get("course_assess", []),
    }
    report = {
        "total_items": len(steps),
        "imported_full": sum(
            1 for step in steps.values() if step.get("fidelity", "full") == "full"
        ),
        "imported_partial": sum(
            1 for step in steps.values() if step.get("fidelity") == "partial"
        ),
        "skipped": 0,
        "warnings": [],
    }
    return pack, report


def _fixture_steps(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    steps_raw = payload.get("steps")
    if not isinstance(steps_raw, dict):
        msg = "fixture missing steps"
        raise ValueError(msg)
    return {
        key: value
        for key, value in steps_raw.items()
        if isinstance(key, str) and isinstance(value, dict)
    }


def _load_fixture(course_id: str) -> dict[str, object]:
    path = _FIXTURES / f"course_{course_id}.json"
    if not path.is_file():
        msg = f"stepik course {course_id} not found in fixtures"
        raise ValueError(msg)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "fixture must be a JSON object"
        raise ValueError(msg)
    return payload
