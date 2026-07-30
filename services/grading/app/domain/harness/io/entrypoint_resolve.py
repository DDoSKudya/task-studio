from __future__ import annotations

from .entrypoint_lang import go_functions, javascript_functions, python_functions


def pick_python_by_arity(
    funcs: list[tuple[str, int | None]],
    arity: int | None,
) -> str | None:
    if arity is None:
        return None
    if matches := [name for name, params in funcs if params is None or params == arity]:
        return matches[0]
    return None


def _first_shared_or_source(source_names: list[str], template_names: list[str]) -> str | None:
    for name in template_names:
        if name in source_names:
            return name
    if source_names:
        return source_names[0]
    return template_names[0] if template_names else None


def resolve_entrypoint(
    *,
    language: str,
    source: str,
    template: str | None,
    entrypoint: str | None,
    arity: int | None,
) -> str | None:
    explicit = entrypoint.strip() if isinstance(entrypoint, str) and entrypoint.strip() else None
    if explicit:
        return explicit

    if language in {"javascript", "js", "node", "typescript"}:
        return _first_shared_or_source(
            javascript_functions(source),
            javascript_functions(template or ""),
        )

    if language in {"go", "golang"}:
        return _first_shared_or_source(
            go_functions(source),
            go_functions(template or ""),
        )

    source_fns = python_functions(source)
    template_fns = python_functions(template or "")
    source_names = [name for name, _ in source_fns]
    template_names = [name for name, _ in template_fns]
    for name in template_names:
        if name in source_names:
            return name
    if not source_fns:
        if template_fns:
            picked = pick_python_by_arity(template_fns, arity)
            return picked or template_fns[0][0]
        return None
    if len(source_fns) == 1:
        return source_fns[0][0]
    picked = pick_python_by_arity(source_fns, arity)
    return picked or source_fns[0][0]
