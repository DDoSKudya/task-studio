from __future__ import annotations

import json
from pathlib import Path

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_PLATFORM = "olx"


def health() -> dict[str, object]:
    return {"status": "ok", "platform": _PLATFORM}


def list_catalog(**_ctx: object) -> list[dict[str, object]]:
    return [{"id": "1", "title": "OLX Course Bundle", "description": "Uploaded OLX archive"}]


def search_remote(*, query: str, **_ctx: object) -> list[dict[str, object]]:
    needle = query.casefold()
    return [item for item in list_catalog() if needle in str(item["title"]).casefold()]


def import_course(*, course_id: str, **_ctx: object) -> tuple[dict[str, object], dict[str, object]]:
    payload = _load_fixture()
    pack = {**payload, "platform": _PLATFORM, "external_id": course_id, "slug": f"olx-{course_id}"}
    return pack, _report(payload)


def _load_fixture() -> dict[str, object]:
    return json.loads((_FIXTURES / "course_1.json").read_text(encoding="utf-8"))


def _report(payload: dict[str, object]) -> dict[str, object]:
    steps = payload.get("steps", {})
    total = len(steps) if isinstance(steps, dict) else 0
    return {
        "total_items": total,
        "imported_full": total - 1,
        "imported_partial": 1,
        "skipped": 0,
        "warnings": [{"step": "video-lesson", "reason": "remote video URL missing in upload"}],
    }
