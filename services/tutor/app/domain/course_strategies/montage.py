from __future__ import annotations

import re

from app.domain.course_strategies.document_blocks import parse_document_blocks

_AUTHOR_BIO = re.compile(
    r"(меня зовут|my name is|привет[,!]?\s+меня|hi[,!]?\s+i'?m\s)",
    re.IGNORECASE,
)
_BANNED_OPENER = re.compile(
    r"^(deep dive|let'?s (?:move|dive|get)|давайте\s+(?:разбер|перейд)|🔥|🚀)",
    re.IGNORECASE,
)


def _bridge(locale: str, index: int, total: int) -> str:

    if index not in {0, total - 1}:
        return ""
    russian = (locale or "ru").casefold().startswith("ru")
    if index == 0:
        return (
            "Ниже — ключевые положения из исходного раздела."
            if russian
            else "Key points from this source section follow."
        )
    return (
        "Итог фрагмента опирается на формулировки источника."
        if russian
        else "This fragment closes on the source wording."
    )


def _append_montage_blocks(
    parts: list[str],
    *,
    excerpt: str,
    locale: str,
) -> None:
    blocks = parse_document_blocks(excerpt, source_prefix="m")
    usable = [
        block
        for block in blocks
        if block.kind in {"paragraph", "code", "list", "table", "figure", "heading"}
        and block.text.strip()
        and not _AUTHOR_BIO.search(block.text)
    ]
    if not usable and excerpt.strip():
        parts.append(" ".join(excerpt.split())[:4_000])
        return

    content_blocks = [block for block in usable if block.kind != "heading"]
    total = max(1, len(content_blocks))
    for index, block in enumerate(content_blocks):
        if block.kind == "code":
            parts.append(f"```{block.lang or ''}\n{block.text.strip()}\n```")
            continue
        if block.kind == "figure" and block.url:
            parts.append(f"![{block.alt or 'figure'}]({block.url})")
            continue
        if block.kind in {"list", "table"}:
            parts.append(_bridge(locale, index, total))
            parts.append(block.text.strip())
            continue
        text = block.text.strip()
        if not _BANNED_OPENER.search(text):
            parts.append(_bridge(locale, index, total))
            parts.append(text)


def _append_missing_claims(
    parts: list[str],
    *,
    key_claims: list[str] | None,
    locale: str,
) -> None:
    if not key_claims:
        return
    content = "\n".join(parts).casefold()
    missing = [claim for claim in key_claims if claim and claim.casefold() not in content]
    if not missing:
        return
    label = "Ключевые утверждения:" if locale.casefold().startswith("ru") else "Key claims:"
    parts.append(label)
    parts.extend(f"- {claim}" for claim in missing[:4])


def montage_theory_from_excerpt(
    *,
    title: str,
    excerpt: str,
    source_images: str = "",
    locale: str = "ru",
    key_claims: list[str] | None = None,
) -> str:

    parts: list[str] = [f"## {title.strip() or 'Topic'}"]
    _append_montage_blocks(parts, excerpt=excerpt, locale=locale)
    figures = (source_images or "").strip()
    if figures and "![" in figures and figures not in "\n".join(parts):
        parts.append(figures)
    _append_missing_claims(parts, key_claims=key_claims, locale=locale)
    body = "\n\n".join(part for part in parts if part and part.strip())
    return body.strip()


def ensure_figures_in_theory(content: str, source_images: str) -> str:
    figures = (source_images or "").strip()
    if not figures or "![" not in figures:
        return content
    if any(line.strip().startswith("![") for line in figures.splitlines() if line.strip()):
        for line in figures.splitlines():
            url_match = re.search(r"\((https?://[^)\s]+)\)", line)
            if url_match and url_match.group(1) in content:
                continue
            if line.strip().startswith("![") and line.strip() not in content:
                content = f"{content.rstrip()}\n\n{line.strip()}"
    return content


def ensure_mermaid_from_visual_plan(
    content: str,
    *,
    visual_plan: dict[str, object] | None,
    title: str = "",
    key_claims: list[str] | None = None,
    locale: str = "ru",
) -> str:

    plan = visual_plan or {}
    plan_type = str(plan.get("type") or "").casefold()
    body = (content or "").strip()
    if plan_type != "mermaid" or "```mermaid" in body:
        return body
    russian = (locale or "ru").casefold().startswith("ru")
    topic = " ".join((title or "Topic").split())[:80] or ("Тема" if russian else "Topic")
    claims = [
        " ".join(str(claim).split())[:90]
        for claim in (key_claims or [])
        if str(claim or "").strip()
    ][:3]
    if not claims:
        claims = [
            "Исходные понятия" if russian else "Core ideas",
            "Практический шаг" if russian else "Practical step",
        ]
    nodes = [f'    A["{topic}"]']
    edges: list[str] = []
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for index, claim in enumerate(claims):
        node_id = labels[index + 1]
        safe = claim.replace('"', "'")
        nodes.append(f'    {node_id}["{safe}"]')
        prev = "A" if index == 0 else labels[index]
        edges.append(f"    {prev} --> {node_id}")
    diagram = "```mermaid\nflowchart TD\n" + "\n".join([*nodes, *edges]) + "\n```"
    caption = (
        "Схема по ключевым утверждениям главы:"
        if russian
        else "Diagram grounded in this chapter's claims:"
    )
    return f"{body}\n\n{caption}\n\n{diagram}".strip()
