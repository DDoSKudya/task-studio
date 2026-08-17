from __future__ import annotations

import html
import re

from app.api.mappers.session_map import build_outline
from app.infra.models import Session
from studio_contracts.api.session_schemas import CourseDigest, CourseDigestStep
from studio_contracts.packs.manifest import get_step


def build_course_digest(learning_session: Session) -> CourseDigest:
    outline = build_outline(learning_session.manifest)
    label_by_id = {
        lesson.step_id: lesson.index_label for topic in outline for lesson in topic.steps
    }
    steps: list[CourseDigestStep] = []
    for topic in outline:
        for lesson in topic.steps:
            raw = get_step(learning_session.manifest, lesson.step_id)
            text = _step_plain_text(raw)
            video = raw.get("video_url") or raw.get("url")
            steps.append(
                CourseDigestStep(
                    step_id=lesson.step_id,
                    topic_id=lesson.topic_id,
                    phase=lesson.phase,
                    kind=lesson.kind,
                    title=lesson.title,
                    index_label=label_by_id.get(lesson.step_id, lesson.index_label),
                    text=text,
                    has_video=isinstance(video, str) and bool(video.strip()),
                )
            )
    return CourseDigest(
        pack_version_id=learning_session.pack_version_id,
        pack_title=learning_session.pack_title,
        steps=steps,
    )


def _step_plain_text(step: dict[str, object], *, limit: int = 1800) -> str:
    chunks: list[str] = []
    seen: set[str] = set()
    for key in (
        "instructions",
        "description",
        "question",
        "text",
        "theory_md",
        "body_md",
        "prompt_md",
        "content",
    ):
        value = step.get(key)
        if not isinstance(value, str):
            continue
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        chunks.append(normalized)
    body_html = step.get("body_html")
    if isinstance(body_html, str) and body_html.strip():
        plain_html = _strip_html(body_html).strip()
        if plain_html and plain_html not in seen:
            chunks.append(plain_html)
    choices = step.get("choices")
    if isinstance(choices, list):
        labeled = [str(item).strip() for item in choices if str(item).strip()]
        if labeled:
            chunks.append("Options: " + " | ".join(labeled[:8]))
    plain = "\n".join(chunks)
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) > limit:
        return plain[: limit - 1].rstrip() + "…"
    return plain


def _strip_html(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", value)
    return html.unescape(no_tags)
