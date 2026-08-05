from __future__ import annotations

from .core import PromptRequest


def skills_for(request: PromptRequest) -> list[str]:
    if request.mode == "pack_studio":
        return []

    if request.mode == "article_from_url":
        skills = [
            "url-to-markdown",
            "article-dechrome",
            "anti-hallucination-source",
            "negative-constraints",
        ]
        if request.compact:
            skills.append("token-budget")
        return skills

    if request.mode == "course_from_article":
        skills = [
            "course-stage-json",
            "anti-hallucination-source",
            "pack-manifest-contract",
            "negative-constraints",
            "instructional-design",
        ]
        stage = (request.step_kind or "").strip().lower()
        if stage == "analyze":
            skills.append("curriculum-synthesis")
        elif stage == "theory":
            skills.append("expand-dense-prose")
            skills.append("diagram-craft")
        elif stage == "polish":
            skills.append("book-polish")
        elif stage == "quizzes":
            skills.append("quiz-assessment-design")
        elif stage == "code":
            skills.append("code-task-ladder")
        elif stage == "tasks":
            skills.append("open-task-ladder")
        elif stage == "consistency":
            skills.append("article-consistency")
        from app.domain.course_from_article.course_profile import profile_skill_overlay

        # Только из запроса — без ContextVar domain (граница prompt ↔ course).
        profile = (request.course_profile or "").strip().casefold().replace("-", "_")
        if profile:
            overlay = profile_skill_overlay(profile)
            if overlay:
                skills.append(overlay)
        # Не вешаем chat-ский token-budget («≤80 words») на генерацию курсов —
        # он убивает смысл статей. Бюджет курса задаётся stage prompts.
        return skills

    if request.mode == "grade":
        skills = ["grade-json-contract", "grade-duty", "grade-evidence", "negative-constraints"]
        kind = request.step_kind.strip().lower()
        if kind == "quiz":
            skills.append("grade-quiz")
        elif kind == "code":
            skills.append("grade-code")
            if request.sql_aware:
                skills.append("sql-coach")
        elif kind == "task":
            skills.append("grade-task")
        elif kind == "lab":
            skills.append("grade-lab")
            skills.append("grade-task")
        if request.compact:
            skills.append("token-budget")
        return skills

    skills: list[str] = ["socratic", "atypical-cases", "negative-constraints"]
    kind = request.step_kind.strip().lower()
    if kind:
        skills.append(f"kind-{kind}")

    if request.mode == "chat" and request.phase == "practice":
        skills.append("attempt-review")
        skills.append("verify-with-checks")
        skills.append("ground-on-page")
        if not request.compact:
            skills.append("light-cot")

    if request.mode == "chat" and request.phase == "study":
        skills.append("ground-on-page")

    if request.mode == "hints":
        if request.compact:
            skills.append("few-shot-hints-compact")
        else:
            skills.append("few-shot-hints")

    if request.sql_aware:
        skills.append("sql-coach")

    if request.compact:
        skills.append("token-budget")

    seen: set[str] = set()
    ordered: list[str] = []
    for name in skills:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def provider_parts(request: PromptRequest) -> list[str]:
    if request.mode == "pack_studio":
        return []
    if request.mode in {"grade", "course_from_article", "article_from_url"}:
        return ["provider/ollama-quality"] if request.compact else ["provider/external"]
    if request.compact:
        return ["provider/ollama-quality"]
    return ["provider/external"]


def role_path(request: PromptRequest) -> str:
    if request.mode == "article_from_url":
        return "roles/article_from_url"
    if request.mode == "course_from_article":
        return "roles/course_from_article"
    if request.mode == "grade":
        return "roles/grade_check"
    if request.mode == "hints":
        return "roles/contextual_hints"
    if request.mode == "pack_studio":
        return "roles/pack_studio"
    if request.phase == "study":
        return "roles/study_chat"
    return "roles/practice_chat"
