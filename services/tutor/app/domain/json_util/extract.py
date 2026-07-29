from __future__ import annotations

import json
import re
from typing import Any

_SMART_QUOTES = str.maketrans(
    {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
    }
)


def extract_json_object(raw: str) -> dict[str, Any] | None:
                                                                                   
    text = _normalize_raw(raw)
    if not text:
        return None
    candidate = _first_balanced_object(text)
    if candidate is None:
        return salvage_truncated_json_object(text)
    parsed = _loads_object(candidate)
    return parsed if parsed is not None else salvage_truncated_json_object(text)


def salvage_truncated_json_object(raw: str) -> dict[str, Any] | None:
                                                                              
    text = _normalize_raw(raw)
    start = text.find("{")
    if start < 0:
        return None
    chunk = text[start:]
    in_string = False
    escape = False
    depth_obj = 0
    depth_arr = 0
    for ch in chunk:
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth_obj += 1
            continue
        if ch == "}":
            depth_obj = max(0, depth_obj - 1)
            continue
        if ch == "[":
            depth_arr += 1
            continue
        if ch == "]":
            depth_arr = max(0, depth_arr - 1)
            continue
    if depth_obj == 0 and depth_arr == 0 and not in_string:
        return _loads_object(chunk)

    closed = chunk.rstrip()
    if closed.endswith(","):
        closed = closed[:-1]
    if in_string:
                                                                              
        if closed.endswith("\\"):
            closed = closed[:-1]
        closed += '"'
    closed += "]" * depth_arr
    closed += "}" * depth_obj
    return _loads_object(closed)


def _normalize_raw(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, count=1, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.translate(_SMART_QUOTES)


def _first_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        ch = text[index]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
            if depth < 0:
                return None
    return None


def _loads_object(candidate: str) -> dict[str, Any] | None:
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None
