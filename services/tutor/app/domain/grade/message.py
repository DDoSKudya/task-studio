from __future__ import annotations

from app.domain.grade.message_extract import (
    as_str,
    first_plain_str,
    looks_like_sql,
    page_text,
    starter_code,
)

__all__ = [
    "as_str",
    "build_grade_user_message",
    "page_text",
    "starter_code",
    "looks_like_sql",
]


def build_grade_user_message(
    *,
    kind: str,
    step: dict[str, object],
    submission: dict[str, object],
) -> str:
    title = as_str(step.get("title")) or as_str(step.get("step_title")) or ""
    page = page_text(step)
    parts = [
        "<step>",
        f"kind: {kind}",
        f"title: {title}" if title else "",
        "</step>",
        f"<task_text>\n{page}\n</task_text>" if page else "<task_text>(empty)</task_text>",
    ]
    if kind == "quiz":
        choices = step.get("choices")
        if isinstance(choices, list):
            lines = []
            for index, choice in enumerate(choices):
                lines.append(f"{index}. {as_str(choice) or str(choice)}")
            parts.append("<choices>\n" + "\n".join(lines) + "\n</choices>")
        choice = submission.get("choice_index")
        if choice is None:
            choice = submission.get("choice")
        parts.append(f"<submission>\nchoice_index: {choice}\n</submission>")
    elif kind in {"task", "lab"}:
        if rubric := as_str(step.get("rubric")):
            parts.append(f"<rubric>\n{rubric[:2000]}\n</rubric>")
        if exemplar := as_str(step.get("exemplar")) or as_str(step.get("answer")):
            parts.append(f"<exemplar_private>\n{exemplar[:2000]}\n</exemplar_private>")
        if kind == "lab":
            lab_meta = step.get("lab") if isinstance(step.get("lab"), dict) else {}
            if isinstance(lab_meta, dict) and (image := as_str(lab_meta.get("image"))):
                parts.append(f"<lab_image>{image}</lab_image>")
            parts.append(
                "<note>Docker lab runner unavailable or not configured — "
                "grade the learner report/notes against the lab instructions.</note>"
            )
        text_s = first_plain_str(
            submission.get("text"),
            submission.get("answer"),
            submission.get("report"),
            submission.get("notes"),
            submission.get("source"),
        )
        parts.append(f"<submission_text>\n{text_s[:4000]}\n</submission_text>")
    else:
        if starter := starter_code(step):
            parts.append(f"<starter>\n{starter[:1200]}\n</starter>")
        if rubric := as_str(step.get("rubric")):
            parts.append(f"<rubric>\n{rubric[:2000]}\n</rubric>")
        source_text = first_plain_str(submission.get("source"))
        parts.append(f"<submission_source>\n{source_text[:4000]}\n</submission_source>")
    parts.append(
        "<request>\nGrade this submission now. You are the last checker — "
        "produce a usable pass/fail when the task text is clear.\n"
        "Output JSON only per contract.\n</request>"
    )
    return "\n\n".join(part for part in parts if part)
