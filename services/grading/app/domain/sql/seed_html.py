from __future__ import annotations

import html
import re
from html.parser import HTMLParser

_TABLE_NAME_RE = re.compile(
    r"(?:таблиц[аеиыу]?|table|from)\s+[«\"`']?([a-zA-Z_][\w]*)[»\"`']?",
    re.IGNORECASE,
)
_IDENT_RE = re.compile(r"^[A-Za-z_][\w]*$")


class HtmlTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.casefold()
        if name == "table":
            self._table = []
        elif name == "tr" and self._table is not None:
            self._row = []
        elif name in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        name = tag.casefold()
        if name in {"td", "th"} and self._cell is not None and self._row is not None:
            text = html.unescape("".join(self._cell)).strip()
            self._row.append(text)
            self._cell = None
        elif name == "tr" and self._row is not None and self._table is not None:
            if any(cell.strip() for cell in self._row):
                self._table.append(self._row)
            self._row = None
        elif name == "table" and self._table is not None:
            if len(self._table) >= 2:
                self.tables.append(self._table)
            self._table = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def guess_table_name(blob: str) -> str | None:
    plain = re.sub(r"<[^>]+>", " ", blob)
    match = _TABLE_NAME_RE.search(plain)
    if not match:
        return None
    name = match.group(1)
    return name if _IDENT_RE.fullmatch(name) else None


def sql_ident(raw: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^\w]+", "_", raw.strip(), flags=re.UNICODE).strip("_")
    if not cleaned:
        return fallback
    if cleaned[0].isdigit():
        cleaned = f"c_{cleaned}"
    return cleaned if _IDENT_RE.fullmatch(cleaned) else fallback


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
