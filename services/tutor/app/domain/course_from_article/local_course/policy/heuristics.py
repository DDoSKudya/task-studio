from __future__ import annotations

import re

from app.domain.course_from_article.common.runtime.course_context import get_course_profile
from app.domain.course_from_article.curriculum.outline.course_locale import normalize_course_locale
from app.domain.course_from_article.curriculum.outline.course_profile import (
    practice_needs_code_starter,
)
from app.domain.course_from_article.quality.assess_quality import quiz_is_usable
from app.domain.ollama.quality_lang import language_mismatch

_TOKEN_RE = re.compile(r"[a-z0-9а-яё]+", re.IGNORECASE)

_INPUT_MARKERS = (
    "given",
    "input",
    "вход",
    "дано",
    "принима",
    "аргумент",
    "параметр",
    "переда",
    "receiv",
    "импорт",
)
_OUTPUT_MARKERS = (
    "expect",
    "output",
    "result",
    "ожида",
    "выход",
    "верн",
    "возвраща",
    "вывед",
    "вывод",
    "результат",
    "ответ",
    "печата",
    "returns",
    "напиш",
    "реализуй",
    "допиши",
)
_SOLVE_DEF_RE = re.compile(r"\bdef\s+solve\s*\(")
_STARTER_NAME_SKIP = frozenset({"a", "an", "and", "class", "def", "for", "solve", "the"})
_FENCE_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)
_OPEN_FENCE_RE = re.compile(r"```(?:\w+)?\n(.*)$", re.DOTALL)
_CODE_LINE_RE = re.compile(
    r"^\s*(?:from\s+\S+\s+import\s+|import\s+[A-Za-z_]|def\s+|class\s+|async\s+def\s+)"
)
_BARE_STARTER_RE = re.compile(r"^(?:\.{1,3}|pass|todo|#\s*starter)?$", re.IGNORECASE)
_DRILL_VERBS = (
    "напиш",
    "создай",
    "добав",
    "импорт",
    "реализуй",
    "допиши",
    "собери",
    "вынес",
    "подключ",
    "сделай",
    "верн",
    "используй",
    "определ",
    "write ",
    "create ",
    "add ",
    "import ",
    "implement ",
    "build ",
    "define ",
    "сравн",
    "перепис",
    "объясн",
    "прокоммент",
    "перевед",
    "опиши",
    "обоснова",
    "compare ",
    "rewrite ",
    "explain ",
    "translate ",
)
_FILLER_BRIEFS = (
    "working code that demonstrates",
    "example that demonstrates",
    "snippet that demonstrates",
    "snippet related to",
    "дано: фрагмент теории",
    "допиши starter так",
    "given: a small",
    "constraints: keep the solution short",
)
_HOOK_RE = re.compile(
    r"(?:/[A-Za-z0-9_\-{}]+)|(?:\b[A-Z][A-Za-z0-9_]{1,}\b)|(?:\b[a-z]+_[a-z0-9_]+\b)"
)


def content_tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.casefold()) if len(token) > 3}


_TEMPLATE_QUIZ_MARKERS = (
    "what is the main goal of",
    "ignore the chapter objective entirely",
    "skip practice and memorize only names",
    "unrelated claim about",
    "когда в этой главе уместен",
    "а не сбор всего в одном месте",
    "stuffing everything into one place",
    "так, как разобрано в тексте главы",
    "the way this chapter's theory describes",
    "проверкой орфографии в комментариях",
    "spell-checking comments",
    "что сломается в шаге главы",
    "если обойти",
    "оставить как было",
    "свести главу к заголовку",
    "в этой главе отличается",
    "потом разберёмся",
    "только как красивое название",
    "можно полностью заменить",
    "достаточно запомнить слово",
    "according to this chapter",
    "по тексту этой главы",
    "ui-only and never takes part",
    "always means the same thing as",
    "enough to replace",
    "with nothing else",
    "без потери смысла шага",
    "не на поведение шага",
    "можно выкинуть из связки",
    "with no change to the step",
    "not the step behavior",
    "alone is enough; drop",
)
_IO_MARKERS = _INPUT_MARKERS + _OUTPUT_MARKERS


def theory_copies_excerpt(content: object, excerpt: str) -> bool:
    body = " ".join(str(content or "").split())
    source = " ".join((excerpt or "").strip().split())
    if len(source) < 40 or len(body) < 40:
        return False
    if body == source:
        return True
    return source in body and len(body) <= len(source) + 120


def quiz_cites_theory(question: str, theory: str) -> bool:
    overlap = content_tokens(question) & content_tokens(theory)
    return len(overlap) >= 1


def quiz_looks_like_template(quiz: dict[str, object]) -> bool:
    choices = quiz.get("choices")
    choice_text = " ".join(str(item) for item in choices) if isinstance(choices, list) else ""
    blob = f"{quiz.get('question') or ''} {choice_text}".casefold()
    return any(marker in blob for marker in _TEMPLATE_QUIZ_MARKERS)


def _quiz_blob(quiz: dict[str, object]) -> str:
    choices = quiz.get("choices")
    choice_text = " ".join(str(item) for item in choices) if isinstance(choices, list) else ""
    return f"{quiz.get('question') or ''} {choice_text}"


def quiz_item_is_usable(
    quiz: dict[str, object],
    *,
    theory: str,
    locale: str | None = "ru",
) -> bool:
    from app.domain.course_strategies import choices_are_letter_only

    if quiz_looks_like_template(quiz):
        return False
    if choices_are_letter_only(quiz.get("choices")):
        return False
    if quiz_choices_are_placeholders(quiz) or quiz_stem_is_multi_answer(quiz):
        return False
    if not quiz_is_usable(quiz):
        return False
    if locale and language_mismatch(_quiz_blob(quiz), normalize_course_locale(locale)):
        return False
    if not quiz_cites_theory(str(quiz.get("question") or ""), theory):
        return False
    return quiz_answer_matches_theory_context(quiz, theory)


def quiz_answer_matches_theory_context(quiz: dict[str, object], theory: str) -> bool:

    choices = quiz.get("choices")
    answer = quiz.get("answer")
    if (
        not isinstance(choices, list)
        or len(choices) != 4
        or isinstance(answer, bool)
        or not isinstance(answer, int)
        or not 0 <= answer < len(choices)
    ):
        return True
    question_terms = content_tokens(str(quiz.get("question") or ""))
    if len(question_terms) < 3:
        return True
    sentences = re.split(r"(?<=[.!?…])\s+|\n+", theory or "")
    scores: list[float] = []
    grounded = 0
    for raw_choice in choices:
        choice = " ".join(str(raw_choice).split()).casefold()
        if len(choice) < 3:
            scores.append(0.0)
            continue
        matching = [sentence for sentence in sentences if choice in sentence.casefold()]
        if not matching:
            scores.append(0.0)
            continue
        grounded += 1
        scores.append(
            max(
                len(question_terms & content_tokens(sentence)) / len(question_terms)
                for sentence in matching
            )
        )
    if grounded < 2:
        return True
    best = max(scores)
    return scores[answer] + 0.2 >= best


def quiz_choices_are_placeholders(quiz: dict[str, object]) -> bool:
    from app.domain.course_strategies import choice_is_placeholder

    choices = quiz.get("choices")
    if not isinstance(choices, list) or not choices:
        return False
    return any(choice_is_placeholder(choice) for choice in choices)


def quiz_stem_is_multi_answer(quiz: dict[str, object]) -> bool:
    from app.domain.course_strategies import stem_wants_many_answers

    return stem_wants_many_answers(str(quiz.get("question") or ""))


def quiz_must_fix(
    quiz: dict[str, object],
    *,
    theory: str,
    locale: str | None = "ru",
) -> list[str]:
    fixes: list[str] = []
    if quiz_looks_like_template(quiz):
        fixes.append("Rewrite an apply/analyze stem; do not ask the chapter's main goal")
    if quiz_choices_are_placeholders(quiz):
        fixes.append('Write real choice texts; never emit "full text …" or "option A"')
    if quiz_stem_is_multi_answer(quiz):
        fixes.append("Ask for exactly one correct answer, not «выберите все правильные»")
    if not quiz_is_usable(quiz):
        fixes.append("Rewrite a concrete stem with four distinct grounded choices")
    if locale and language_mismatch(_quiz_blob(quiz), normalize_course_locale(locale)):
        code = normalize_course_locale(locale)
        name = "Russian" if code == "ru" else "English"
        fixes.append(f"Write the stem and all four choices in {name} ({code}) only")
    if not quiz_cites_theory(str(quiz.get("question") or ""), theory):
        fixes.append("Use key terms from the chapter theory in the question stem")
    elif not quiz_answer_matches_theory_context(quiz, theory):
        fixes.append("Correct the answer index: it contradicts the matching theory sentence")
    return fixes


def _need_code_starter(require_starter: bool | None) -> bool:
    if require_starter is not None:
        return require_starter
    return practice_needs_code_starter(get_course_profile())


def practice_must_fix(
    task: dict[str, object],
    *,
    locale: str | None = "ru",
    theory: str = "",
    require_starter: bool | None = None,
) -> list[str]:
    need_starter = _need_code_starter(require_starter)
    if practice_spec_is_usable(task, locale=locale, theory=theory, require_starter=need_starter):
        return []
    normalized = normalize_practice_task(task, theory=theory)
    code = normalize_course_locale(locale or "ru")
    brief = str(normalized.get("content") or "")
    template = str(normalized.get("template") or "")
    fixes: list[str] = []
    if locale and language_mismatch(brief, code):
        name = "Russian" if code == "ru" else "English"
        fixes.append(f"Rewrite the brief in {name} ({code}) only")
    if len(brief.strip()) < 40:
        if need_starter:
            if code == "ru":
                fixes.append("Напиши одно-два предложения: какой шаг дописать в коде")
            else:
                fixes.append("Write one or two sentences: which step to complete in the starter")
        elif code == "ru":
            fixes.append("Напиши одно-два предложения: что сравнить, переписать или ответить")
        else:
            fixes.append("Write one or two sentences: compare, rewrite, or answer from the chapter")
    if not brief_looks_like_drill(brief):
        if code == "ru":
            fixes.append("Сформулируй конкретный шаг главы, не экзамен «Дано/Ожидается»")
        else:
            fixes.append("State the chapter step to repeat; do not write an exam prompt")
    if need_starter and starter_is_blank(template):
        if code == "ru":
            fixes.append("Оставь непустой стартовый код в template")
        else:
            fixes.append("Keep a non-empty starter template")
    if practice_looks_like_template(normalized):
        fixes.append("Name a domain function; do not use a generic solve() stub")
    if need_starter:
        return fixes or ["Rewrite a concrete coding task from the chapter"]
    return fixes or ["Rewrite a short chapter drill without inventing code"]


def practice_looks_like_template(task: dict[str, object]) -> bool:
    content = str(task.get("content") or "").casefold()
    template = str(task.get("template") or "").casefold()
    if any(phrase in content for phrase in _FILLER_BRIEFS):
        return True
    if "def solve(" in template:
        return True
    return "notimplementederror" in template.replace(" ", "")


def brief_looks_like_drill(content: str) -> bool:
    text = (content or "").strip()
    if len(text) < 40:
        return False
    lowered = text.casefold()
    if any(phrase in lowered for phrase in _FILLER_BRIEFS):
        return False
    if _brief_has_code(text):
        return True
    if any(verb in lowered for verb in _DRILL_VERBS):
        return True
    if any(marker in lowered for marker in _IO_MARKERS):
        return True
    return _HOOK_RE.search(text) is not None


def starter_from_code_lines(content: str) -> str:
    lines = [line for line in (content or "").splitlines() if _CODE_LINE_RE.match(line)]
    if not lines:
        return ""
    return "\n".join(lines).strip()


def starter_from_brief(content: str) -> str:
    match = _FENCE_RE.search(content or "")
    if match is not None:
        return match.group(1).strip()
    opened = _OPEN_FENCE_RE.search(content or "")
    if opened is not None:
        body = opened.group(1).split("```", 1)[0].strip()
        if len(body) >= 12:
            return body
    return starter_from_code_lines(content)


def starter_is_blank(template: str) -> bool:
    text = (template or "").strip()
    if len(text) < 20 or _BARE_STARTER_RE.fullmatch(text):
        return True
    code = "\n".join(
        line for line in text.splitlines() if line.strip() and not line.strip().startswith("#")
    )
    return len(code.strip()) < 12


def recover_practice_starter(*, template: str, content: str, theory: str = "") -> str:
    if not starter_is_blank(template):
        return template.strip()
    for blob in (content, theory):
        recovered = starter_from_brief(blob)
        if not starter_is_blank(recovered):
            return recovered[:800]
    return template


def starter_function_name(title: str) -> str:
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_]*", title or ""):
        folded = token.casefold()
        if folded not in _STARTER_NAME_SKIP:
            return folded
    return "task"


def rewrite_generic_starter(template: str, title: str) -> str:
    if not template or _SOLVE_DEF_RE.search(template) is None:
        return template
    return _SOLVE_DEF_RE.sub(f"def {starter_function_name(title)}(", template, count=1)


def _brief_has_code(content: str) -> bool:
    return bool(_FENCE_RE.search(content or "") or starter_from_code_lines(content))


def normalize_practice_task(
    task: dict[str, object],
    *,
    theory: str = "",
) -> dict[str, object]:
    out = dict(task)
    content = _practice_field_text(out.get("content"))
    original = _practice_field_text(out.get("template") or out.get("starter") or out.get("code"))
    recovered = recover_practice_starter(template=original, content=content, theory=theory)
    out["content"] = content or str(out.get("content") or "")
    out["template"] = rewrite_generic_starter(recovered, str(out.get("title") or ""))
    return out


def _practice_field_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _strip_code_fence(value.strip())
    if isinstance(value, list | tuple):
        parts = [_practice_field_text(item) for item in value]
        return "\n".join(part for part in parts if part).strip()
    if isinstance(value, dict):
        for key in (
            "template",
            "starter",
            "starter_code",
            "code",
            "content",
            "text",
            "brief",
            "java",
            "python",
            "go",
            "javascript",
            "typescript",
            "start",
            "body",
        ):
            if key in value:
                text = _practice_field_text(value.get(key))
                if text:
                    return text
        return ""
    return str(value).strip()


_FENCE_BLOCK_RE = re.compile(
    r"^```(?:[a-zA-Z0-9_+-]+)?\s*\n(.*?)```\s*$",
    re.DOTALL,
)


def _strip_code_fence(text: str) -> str:
    match = _FENCE_BLOCK_RE.match((text or "").strip())
    if match is not None:
        return match.group(1).strip()
    return (text or "").strip()


def starter_matches_runtime(template: str, runtime: str) -> bool:

    code = (template or "").strip()
    if len(code) < 12:
        return True
    lang = (runtime or "python").casefold()
    has_def = bool(re.search(r"\bdef\s+\w+\s*\(", code))
    has_java = bool(
        re.search(r"\bpublic\s+class\b", code)
        or re.search(r"\bvoid\s+main\s*\(", code)
        or "import org.apache" in code
    )
    if lang == "java" and has_def and not has_java:
        return False
    return not (lang.startswith("python") and has_java and not has_def)


def practice_spec_is_usable(
    task: dict[str, object],
    *,
    locale: str | None = "ru",
    theory: str = "",
    require_starter: bool | None = None,
    runtime: str | None = None,
) -> bool:
    task = normalize_practice_task(task, theory=theory)
    title = str(task.get("title") or "").strip()
    content = str(task.get("content") or "").strip()
    template = str(task.get("template") or "").strip()
    if practice_looks_like_template(task):
        return False
    if len(title) < 8 or len(content) < 40:
        return False
    if _need_code_starter(require_starter) and starter_is_blank(template):
        return False
    if runtime and not starter_matches_runtime(template, runtime):
        return False
    if locale and language_mismatch(content, normalize_course_locale(locale)):
        return False
    return brief_looks_like_drill(content)
