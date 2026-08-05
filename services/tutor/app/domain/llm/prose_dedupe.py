from __future__ import annotations

import re

_THROAT_CLEARING_LINE = re.compile(
    r"^(?:#{1,3}\s+)?("
    r"(?:в\s+(?:этой|данной)\s+главе[^.!?]{0,160}[.!?])|"
    r"(?:in\s+this\s+chapter[^.!?]{0,160}[.!?])|"
    r"(?:it\s+is\s+important\s+to\s+note[^.!?]{0,120}[.!?])|"
    r"(?:важно\s+(?:отметить|понимать|запомнить)[^.!?]{0,120}[.!?])|"
    r"(?:давайте\s+(?:рассмотрим|разберём|изучим)[^.!?]{0,120}[.!?])|"
    r"(?:we\s+will\s+(?:explore|discuss|learn)[^.!?]{0,120}[.!?])"
    r")\s*$",
    re.IGNORECASE,
)


def strip_throat_clearing(text: str, *, max_passes: int = 4) -> str:
    """Remove filler intros that add length without teaching."""
    body = (text or "").strip()
    if not body:
        return body
    paragraphs = re.split(r"\n\s*\n+", body)
    for _ in range(max_passes):
        if not paragraphs:
            break
        head = paragraphs[0].strip()
        if not head or not _THROAT_CLEARING_LINE.match(head):
            break
        paragraphs.pop(0)
    return "\n\n".join(paragraphs).strip()


def collapse_repeated_prose(text: str, *, min_block: int = 240) -> str:
    """Drop generation loops where the same lesson block is pasted many times."""
    body = (text or "").strip()
    if len(body) < min_block * 2:
        return body

    max_period = min(len(body) // 2, 3_200)
    for period in range(min_block, max_period + 1):
        if body[:period] == body[period : period * 2]:
            return body[:period].rstrip()

    # Prefix reappears later (restart mid-string / continue paste).
    for size in range(min(max_period, 1_200), min_block, -20):
        needle = body[:size]
        hit = body.find(needle, size)
        if hit != -1:
            return body[:hit].rstrip()

    return _collapse_ngram_run(body, window=min(200, min_block))


def continuation_is_restart(assembled: str, chunk: str) -> bool:
    """True when a continue call restarts the chapter instead of appending."""
    head = (assembled or "").strip()
    piece = (chunk or "").strip()
    if len(head) < 80 or len(piece) < 80:
        return False
    probe = head[: min(180, len(head))]
    if piece.startswith(probe[:120]):
        return True
    return probe[:140] in piece[: min(500, len(piece))]


def _collapse_ngram_run(text: str, *, window: int) -> str:
    if len(text) < window * 4:
        return text
    step = max(24, window // 5)
    positions: dict[str, list[int]] = {}
    for index in range(0, len(text) - window + 1, step):
        gram = text[index : index + window]
        bucket = positions.setdefault(gram, [])
        bucket.append(index)
        if len(bucket) >= 3 and bucket[0] < len(text) // 2:
            return text[: bucket[1]].rstrip()
    return text
