from __future__ import annotations

import re
from typing import Literal

ReplyLanguage = Literal["ru", "en"]

_UNEXPECTED_SCRIPT_RE = re.compile(
    "["
    "\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff"
    "\u4e00-\u9fff\u3400-\u4dbf"
    "\u3040-\u30ff"
    "\uac00-\ud7af"
    "\u0590-\u05ff"
    "\u0e00-\u0e7f"
    "\u0900-\u097f"
    "]"
)
_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_RE = re.compile(r"`[^`]+`")

LANGUAGE_NAMES: dict[ReplyLanguage, str] = {
    "ru": "Russian",
    "en": "English",
}


def infer_reply_language(message: str) -> ReplyLanguage:
    letters = [ch for ch in message if ch.isalpha()]
    if not letters:
        return "ru"
    cyrillic = sum("\u0400" <= ch <= "\u04ff" for ch in letters)
    if cyrillic / len(letters) >= 0.25:
        return "ru"
    return "en"


def prose_without_code(text: str) -> str:
    cleaned = _CODE_FENCE_RE.sub(" ", text)
    return _INLINE_CODE_RE.sub(" ", cleaned)


def has_unexpected_scripts(text: str) -> bool:
    return bool(_UNEXPECTED_SCRIPT_RE.search(prose_without_code(text)))


def language_mismatch(text: str, language: ReplyLanguage) -> bool:

    prose = prose_without_code(text)
    letters = [ch for ch in prose if ch.isalpha()]
    if len(letters) < 40:
        return False
    cyrillic = sum("\u0400" <= ch <= "\u04ff" for ch in letters)
    ratio = cyrillic / len(letters)
    if language == "ru":
        return ratio < 0.2
    return ratio > 0.65


def needs_quality_retry(text: str, language: ReplyLanguage) -> bool:
    return has_unexpected_scripts(text) or language_mismatch(text, language)
