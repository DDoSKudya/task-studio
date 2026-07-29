from __future__ import annotations

_ENTRY_FILES: dict[str, str] = {
    "python": "main.py",
    "javascript": "main.js",
    "go": "main.go",
    "sql": "main.sql",
    "sqlite3": "main.sql",
}

_PISTON_LANGUAGE: dict[str, tuple[str, str]] = {
    "sql": ("sqlite3", "*"),
}


def piston_entry_name(language: str, mapped_language: str) -> str:
    return _ENTRY_FILES.get(mapped_language, _ENTRY_FILES.get(language, "main.txt"))


def map_piston_language(language: str, version: str) -> tuple[str, str]:
    return _PISTON_LANGUAGE.get(language.casefold(), (language, version))
