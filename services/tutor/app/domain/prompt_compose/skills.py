from __future__ import annotations

from .core import PromptRequest

_COURSE_ALWAYS_SKILLS = (
    "course-stage-json",
    "anti-hallucination-source",
    "pack-manifest-contract",
    "negative-constraints",
    "instructional-design",
)
_COURSE_STAGE_SKILLS: dict[str, tuple[str, ...]] = {
    "analyze": ("curriculum-synthesis",),
    "theory": ("expand-dense-prose", "diagram-craft"),
    "polish": ("book-polish",),
    "quizzes": ("quiz-assessment-design",),
    "code": ("code-task-ladder", "practice-as-drill"),
    "tasks": ("open-task-ladder", "practice-as-drill"),
    "quality": ("chapter-quality-gate",),
}


def course_skill_layers(request: PromptRequest) -> tuple[list[str], list[str], list[str]]:

    from app.domain.course_from_article.common.runtime.course_context import get_course_parts
    from app.domain.course_from_article.curriculum.outline.course_profile import (
        profile_skill_overlay,
    )
    from app.domain.course_strategies import filter_skills_for_pack, parse_strategy_pack

    always: list[str] = list(_COURSE_ALWAYS_SKILLS)
    domain = [profile_skill_overlay(request.course_profile or "")]
    stage: list[str] = list(_COURSE_STAGE_SKILLS.get((request.step_kind or "").strip().lower(), ()))
    flags = get_course_parts()
    if not flags.quizzes:
        stage = [name for name in stage if name != "quiz-assessment-design"]
    if not flags.practice:
        stage = [
            name
            for name in stage
            if name not in {"code-task-ladder", "practice-as-drill", "open-task-ladder"}
        ]
    if pack_id := (request.strategy_pack or "").strip():
        pack = parse_strategy_pack(pack_id)

        always = filter_skills_for_pack(always, pack)
        stage = filter_skills_for_pack(stage, pack)
    return always, domain, stage


_GRADE_KIND_SKILLS: dict[str, tuple[str, ...]] = {
    "quiz": ("grade-quiz",),
    "code": ("grade-code",),
    "task": ("grade-task",),
    "lab": ("grade-lab", "grade-task"),
}


def _article_from_url_skills(request: PromptRequest) -> list[str]:
    skills = [
        "url-to-markdown",
        "article-dechrome",
        "anti-hallucination-source",
        "negative-constraints",
    ]
    if request.compact:
        skills.append("token-budget")
    return skills


def _grade_skills(request: PromptRequest) -> list[str]:
    kind = request.step_kind.strip().lower()
    skills = [
        "grade-json-contract",
        "grade-duty",
        "grade-evidence",
        "negative-constraints",
        *_GRADE_KIND_SKILLS.get(kind, ()),
    ]
    if kind == "code" and request.sql_aware:
        skills.append("sql-coach")
    if request.compact:
        skills.append("token-budget")
    return skills


def _chat_hint_skills(request: PromptRequest) -> list[str]:
    skills: list[str] = ["socratic", "atypical-cases", "negative-constraints"]
    if kind := request.step_kind.strip().lower():
        skills.append(f"kind-{kind}")
    if request.mode == "chat":
        match request.phase:
            case "practice":
                skills.extend(("attempt-review", "verify-with-checks", "ground-on-page"))
                if not request.compact:
                    skills.append("light-cot")
            case "study":
                skills.append("ground-on-page")
    if request.mode == "hints":
        skills.append("few-shot-hints-compact" if request.compact else "few-shot-hints")
    if request.sql_aware:
        skills.append("sql-coach")
    if request.compact:
        skills.append("token-budget")
    return list(dict.fromkeys(skills))


def skills_for(request: PromptRequest) -> list[str]:
    match request.mode:
        case "pack_studio":
            return []
        case "article_from_url":
            return _article_from_url_skills(request)
        case "course_from_article":
            always, domain, stage = course_skill_layers(request)
            return [*always, *domain, *stage]
        case "grade":
            return _grade_skills(request)
        case _:
            return _chat_hint_skills(request)


def provider_parts(request: PromptRequest) -> list[str]:
    if request.mode == "pack_studio":
        return []
    if request.mode in {"grade", "course_from_article", "article_from_url"}:
        if request.compact or request.local_runtime:
            return ["provider/ollama-quality"]
        return ["provider/external"]
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
