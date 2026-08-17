from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

BlockKind = Literal["heading", "paragraph", "code", "figure", "list", "table"]

_HEADING = re.compile(r"^(#{1,3})\s+(\S.*?)\s*$")
_FIGURE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_FENCE = re.compile(r"^```(\w*)\s*$")
_TABLE_ROW = re.compile(r"^\|")
_LIST_ITEM = re.compile(r"^(\s*[-*+]|\s*\d+[.)])\s+")


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    block_id: str
    kind: BlockKind
    text: str
    level: int = 0
    lang: str = ""
    url: str = ""
    alt: str = ""


def parse_document_blocks(markdown: str, *, source_prefix: str = "src") -> list[DocumentBlock]:

    lines = (markdown or "").splitlines()
    blocks: list[DocumentBlock] = []
    index = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if match := _HEADING.match(stripped):
            index += 1
            blocks.append(
                DocumentBlock(
                    block_id=f"{source_prefix}-b{index}",
                    kind="heading",
                    text=match.group(2).strip(),
                    level=len(match.group(1)),
                )
            )
            i += 1
            continue
        if fence := _FENCE.match(stripped):
            lang = fence.group(1) or ""
            body: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            index += 1
            blocks.append(
                DocumentBlock(
                    block_id=f"{source_prefix}-b{index}",
                    kind="code",
                    text="\n".join(body).strip(),
                    lang=lang.casefold(),
                )
            )
            continue
        if _FIGURE.search(stripped):
            for fig in _FIGURE.finditer(stripped):
                index += 1
                blocks.append(
                    DocumentBlock(
                        block_id=f"{source_prefix}-b{index}",
                        kind="figure",
                        text=fig.group(0),
                        alt=fig.group(1).strip(),
                        url=fig.group(2).strip(),
                    )
                )
            i += 1
            continue
        if _TABLE_ROW.match(stripped):
            rows = [stripped]
            i += 1
            while i < len(lines) and _TABLE_ROW.match(lines[i].strip()):
                rows.append(lines[i].strip())
                i += 1
            index += 1
            blocks.append(
                DocumentBlock(
                    block_id=f"{source_prefix}-b{index}",
                    kind="table",
                    text="\n".join(rows),
                )
            )
            continue
        if _LIST_ITEM.match(line):
            items = [stripped]
            i += 1
            while i < len(lines) and _LIST_ITEM.match(lines[i]):
                items.append(lines[i].strip())
                i += 1
            index += 1
            blocks.append(
                DocumentBlock(
                    block_id=f"{source_prefix}-b{index}",
                    kind="list",
                    text="\n".join(items),
                )
            )
            continue
        para = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (
                not nxt
                or _HEADING.match(nxt)
                or _FENCE.match(nxt)
                or _FIGURE.search(nxt)
                or _TABLE_ROW.match(nxt)
                or _LIST_ITEM.match(lines[i])
            ):
                break
            para.append(nxt)
            i += 1
        index += 1
        blocks.append(
            DocumentBlock(
                block_id=f"{source_prefix}-b{index}",
                kind="paragraph",
                text=" ".join(para),
            )
        )
    return blocks


def blocks_from_sources(sources: list[dict[str, object]]) -> list[DocumentBlock]:
    out: list[DocumentBlock] = []
    for src_index, item in enumerate(sources, start=1):
        content = str(item.get("content") or "")
        prefix = f"s{src_index}"
        out.extend(parse_document_blocks(content, source_prefix=prefix))
    return out
