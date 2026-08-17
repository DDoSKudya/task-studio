from __future__ import annotations

import re

from app.domain.course.page import (
    PAGE_CONTENT_LIMIT,
    STARTER_CODE_LIMIT,
    starter_code,
    step_page_text,
    strip_html,
)
from studio_contracts.api.session_schemas import CourseDigest, CourseDigestStep, StepContent

_starter_code = starter_code
_strip_html = strip_html

__all__ = [
    "step_page_text",
    "find_digest_step",
    "format_course_outline",
    "format_step_context",
    "parse_hint_lines",
]


def find_digest_step(digest: CourseDigest, step_id: str) -> CourseDigestStep | None:
    for item in digest.steps:
        if item.step_id == step_id:
            return item
    return None


def format_course_outline(digest: CourseDigest, *, max_steps: int = 80) -> str:
    lines = [f"Course: {digest.pack_title}", "Steps:"]
    for item in digest.steps[:max_steps]:
        lines.append(f"- [{item.index_label}] ({item.kind}/{item.phase}) {item.title}")
    if len(digest.steps) > max_steps:
        lines.append(f"… and {len(digest.steps) - max_steps} more steps")
    body = "\n".join(lines)
    return f"<course_outline>\n{body}\n</course_outline>"


def format_step_context(
    digest: CourseDigest,
    step: StepContent,
    *,
    page_limit: int = PAGE_CONTENT_LIMIT,
    starter_limit: int = STARTER_CODE_LIMIT,
) -> str:
    entry = find_digest_step(digest, step.step_id)
    index_label = entry.index_label if entry else step.step_id
    page = step_page_text(step) or (entry.text if entry else "")
    has_video = entry.has_video if entry else step.kind == "video"
    parts = [
        f"Step: [{index_label}] {step.title}",
        f"Kind: {step.kind}",
        f"Phase: {step.phase}",
        "Primary context: prefer this page over older chat turns.",
    ]
    if has_video and not page:
        parts.append("Media: video only — textual hints from transcript/content are unavailable.")
    if page:
        clipped = page if len(page) <= page_limit else page[: page_limit - 1].rstrip() + "…"
        parts.append(f"<page_content>\n{clipped}\n</page_content>")
    if starter := starter_code(step, limit=starter_limit):
        parts.append(f"<starter_code>\n{starter}\n</starter_code>")
    body = "\n".join(parts)
    return f"<current_page>\n{body}\n</current_page>"


def parse_hint_lines(raw: str, *, limit: int = 4) -> list[str]:
    lines: list[str] = []
    for line in raw.splitlines():
        if cleaned := re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip():
            lines.append(cleaned)
        if len(lines) >= limit:
            break
    return lines
