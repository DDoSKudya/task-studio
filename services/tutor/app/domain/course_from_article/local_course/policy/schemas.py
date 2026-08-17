from __future__ import annotations

from collections.abc import Mapping

import httpx
from app.domain.llm.target import LlmTarget

ORDER_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "order": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "outcomes": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 6,
        },
        "merge_groups": {
            "type": "array",
            "items": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
            },
            "maxItems": 24,
        },
    },
    "required": ["order"],
}

LABEL_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "chapters": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "objective": {"type": "string"},
                },
                "required": ["id", "title"],
            },
        },
        "outcomes": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 6,
        },
    },
    "required": ["chapters"],
}

_QUIZ_ITEM_PROPERTIES: dict[str, object] = {
    "title": {"type": "string"},
    "question": {"type": "string", "minLength": 12},
    "choices": {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
        "minItems": 4,
        "maxItems": 4,
    },
    "answer": {"type": "integer", "minimum": 0, "maximum": 3},
}

QUIZ_ITEM_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": _QUIZ_ITEM_PROPERTIES,
    "required": ["question", "choices", "answer"],
}

QUIZ_BATCH_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "quizzes": {
            "type": "array",
            "minItems": 1,
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": _QUIZ_ITEM_PROPERTIES,
                "required": ["question", "choices", "answer"],
            },
        }
    },
    "required": ["quizzes"],
}

PRACTICE_ITEM_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "minLength": 8},
        "content": {"type": "string", "minLength": 40},
        "template": {"type": "string"},
        "level": {"type": "string"},
    },
    "required": ["title", "content"],
}

PRACTICE_BATCH_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": PRACTICE_ITEM_SCHEMA,
        }
    },
    "required": ["tasks"],
}


def schema_prompt_hint(schema: Mapping[str, object]) -> str:
    return f"Respond with JSON only that matches this schema (no markdown fences):\n{dict(schema)}"


def parse_json_object(raw: str) -> dict[str, object]:
    from app.domain.json_util.extract import extract_json_object

    parsed = extract_json_object(raw)
    if parsed is None:
        msg = "expected JSON object"
        raise ValueError(msg)
    return parsed


async def load_json_object(
    client: httpx.AsyncClient,
    target: LlmTarget,
    raw: str,
    *,
    hint: str,
    max_tokens: int = 1200,
    num_ctx: int | None = None,
) -> dict[str, object]:
    from app.domain.json_util.repair import parse_or_repair_json

    parsed = await parse_or_repair_json(
        client,
        target,
        raw=raw,
        hint=hint,
        max_tokens=max_tokens,
        num_ctx=num_ctx,
    )
    if parsed is None:
        msg = "expected JSON object"
        raise ValueError(msg)
    return parsed


def payload_items(
    payload: dict[str, object],
    *,
    plural: str,
    singular: str,
) -> list[object]:
    folded = {str(key).casefold(): value for key, value in payload.items()}
    raw = folded.get(plural.casefold())
    if isinstance(raw, list):
        return raw
    one = folded.get(singular.casefold())
    if isinstance(one, dict):
        return [one]
    if folded.get("question") or folded.get("choices") or folded.get("options"):
        return [payload]

    if folded.get("title") or folded.get("content") or folded.get("template"):
        return [payload]
    return []
