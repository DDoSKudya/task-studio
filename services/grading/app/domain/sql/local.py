from __future__ import annotations

from app.domain.sql.seed import (
    HtmlTableParser,
    build_sql_seed,
    guess_table_name,
    sql_ident,
    sql_literal,
)

__all__ = [
    "build_sql_seed",
    "looks_like_sql_step",
]

                                         
_HtmlTableParser = HtmlTableParser
_guess_table_name = guess_table_name
_sql_ident = sql_ident
_sql_literal = sql_literal


def looks_like_sql_step(step: dict[str, object]) -> bool:
    runtime = str(step.get("runtime") or "").casefold()
    reply = str(step.get("stepik_reply") or "").casefold()
    return runtime == "sql" or reply in {"solve_sql", "sql"}
