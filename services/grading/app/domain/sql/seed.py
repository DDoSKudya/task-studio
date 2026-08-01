from __future__ import annotations

from app.domain.sql.seed_html import HtmlTableParser, guess_table_name, sql_ident, sql_literal

__all__ = [
    "HtmlTableParser",
    "build_sql_seed",
    "guess_table_name",
    "sql_ident",
    "sql_literal",
]


def build_sql_seed(step: dict[str, object]) -> str | None:
    explicit = step.get("sql_seed")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip().rstrip(";") + ";"

    raw_parts: list[str] = []
    for key in ("body_html", "instructions", "description", "question", "text"):
        value = step.get(key)
        if isinstance(value, str) and value.strip():
            raw_parts.append(value)
    content = step.get("content")
    if isinstance(content, dict):
        for key in ("body_html", "instructions", "description"):
            value = content.get(key)
            if isinstance(value, str) and value.strip():
                raw_parts.append(value)
    blob = "\n".join(raw_parts)
    if not blob.strip():
        return None

    parser = HtmlTableParser()
    try:
        parser.feed(blob)
    except (ValueError, TypeError, AssertionError):
        return None
    if not parser.tables:
        return None

    table_name = guess_table_name(blob) or "data"

    grid = max(parser.tables, key=lambda rows: len(rows) * max(len(row) for row in rows))
    header = [sql_ident(cell, fallback=f"col{index + 1}") for index, cell in enumerate(grid[0])]
    if not header:
        return None

    lines = [
        f"DROP TABLE IF EXISTS {table_name};",
        f"CREATE TABLE {table_name} (",
        ",\n".join(f"  {column} TEXT" for column in header),
        ");",
    ]
    for row in grid[1:]:
        values = [
            sql_literal(row[index] if index < len(row) else "") for index in range(len(header))
        ]
        lines.append(
            f"INSERT INTO {table_name} ({', '.join(header)}) VALUES ({', '.join(values)});"
        )
    return "\n".join(lines)
