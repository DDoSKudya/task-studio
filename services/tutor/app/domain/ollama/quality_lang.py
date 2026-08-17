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
_MIXED_SCRIPT_TOKEN_RE = re.compile(
    r"(?=[\w]*[A-Za-z])(?=[\w]*[\u0400-\u04ff])[\w\u0400-\u04ff]{3,}"
)

_LEADING_CYR_TECH_RE = re.compile(
    r"(?<![A-Za-z\u0400-\u04ff])([\u0400-\u04ff])([A-Za-z][A-Za-z0-9_-]{1,})"
)
_CYR_FIRST_TO_LATIN = str.maketrans(
    {
        "А": "A",
        "а": "a",
        "В": "B",
        "Е": "E",
        "е": "e",
        "К": "K",
        "к": "k",
        "М": "M",
        "Н": "H",
        "О": "O",
        "о": "o",
        "Р": "P",
        "р": "p",
        "С": "C",
        "с": "c",
        "Т": "T",
        "Х": "X",
        "х": "x",
        "Д": "D",
        "д": "d",
        "З": "Z",
        "з": "z",
    }
)
_TRANSLIT_NOISE_RE = re.compile(
    r"(?i)("
    r"\bkomputer\b|\bcomputor\b|\bcompputer\b|"
    r"комputer|кomputer|"
    r"видаен|"
    r"\bvideenii\b|\bvidaenii\b|"
    r"klassifikat|"
    r"segmenats|"
    r"detekts"
    r")"
)

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


def has_script_mixing(text: str) -> bool:
    prose = prose_without_code(text)
    if _MIXED_SCRIPT_TOKEN_RE.search(prose):
        return True
    return bool(_TRANSLIT_NOISE_RE.search(prose))


def repair_script_mixing(text: str) -> str:

    def _leading(match: re.Match[str]) -> str:
        head = match.group(1)
        tail = match.group(2)
        mapped = head.translate(_CYR_FIRST_TO_LATIN)
        return match.group(0) if mapped == head else f"{mapped}{tail}"

    def _token(match: re.Match[str]) -> str:
        token = match.group(0)
        latin = sum(ch.isascii() and ch.isalpha() for ch in token)
        cyrillic = sum("\u0400" <= ch <= "\u04ff" for ch in token)
        return token.translate(_CYR_FIRST_TO_LATIN) if latin >= cyrillic else token

    repaired = _LEADING_CYR_TECH_RE.sub(_leading, text or "")
    return _MIXED_SCRIPT_TOKEN_RE.sub(_token, repaired)


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
    if has_unexpected_scripts(text) or language_mismatch(text, language):
        return True
    return bool(language == "ru" and has_script_mixing(text))
