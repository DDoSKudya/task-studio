from __future__ import annotations

import re

from app.domain.course_from_article.common.content.textutil import _slug
from app.domain.course_from_article.curriculum.outline.course_locale import normalize_course_locale
from app.domain.course_from_article.local_course.policy.heuristics import (
    content_tokens,
    practice_spec_is_usable,
    quiz_item_is_usable,
    starter_from_brief,
    starter_function_name,
    starter_is_blank,
    starter_matches_runtime,
)

_HOOK_RE = re.compile(
    r"(?:/[A-Za-z0-9_\-{}]+)|(?:\b[A-Z][A-Za-z0-9_]{1,}\b)|(?:\b[a-z]+_[a-z0-9_]+\b)"
)
_STOP = frozenset(
    {
        "this",
        "that",
        "with",
        "from",
        "have",
        "been",
        "will",
        "your",
        "their",
        "chapter",
        "theory",
        "which",
        "when",
        "what",
        "about",
        "into",
        "only",
        "keep",
        "used",
        "using",
        "этот",
        "этой",
        "этого",
        "глава",
        "главы",
        "нужно",
        "можно",
        "после",
        "перед",
        "также",
        "более",
        "между",
        "через",
        "если",
        "когда",
        "чтобы",
        "listing",
        "function",
        "append",
        "print",
        "true",
        "false",
        "none",
        "null",
    }
)
# Отсекает глагольные/причастные обрывки вроде «храниться», «определяющий».
_WEAK_TERM_RE = re.compile(
    r"(?:"
    r".*(?:ущий|ющий|ающий|яющий|вший|енный|ённый|анный)$|"
    r".*(?:ить|ать|ять|еть|тись|ться)$|"
    r".*(?:ится|ается|ется|ятся|аются)$"
    r")",
    re.IGNORECASE,
)


def template_quizzes_from_objective(
    *,
    chapter: dict[str, str],
    count: int,
    topic_key: str,
    theory: str = "",
) -> list[dict[str, object]]:
    objective = str(chapter.get("objective") or chapter.get("title") or "topic").strip()
    title = str(chapter.get("title") or "Topic").strip()
    anchor = " ".join((theory or objective).split())[:120]
    quizzes: list[dict[str, object]] = []
    stems = (
        f"What is the main goal of «{title}» when you {anchor}?",
        f"Which statement best matches: {objective[:120]} ({anchor})?",
        f"What should you avoid when applying «{title}» to {anchor}?",
    )
    for index in range(max(0, min(count, 3))):
        stem = stems[index % len(stems)]
        quizzes.append(
            {
                "id": _slug(f"{topic_key}-quiz-t{index + 1}")[:96],
                "kind": "quiz",
                "title": f"Check: {title}"[:120],
                "question": stem[:400],
                "choices": [
                    objective[:160] or f"Correct idea about {title}",
                    f"Unrelated claim about {title}",
                    "Ignore the chapter objective entirely",
                    "Skip practice and memorize only names",
                ],
                "answer": 0,
            }
        )
    return quizzes


def template_practice_from_objective(
    *,
    chapter: dict[str, str],
    count: int,
    topic_key: str,
    runtime: str = "python",
) -> list[dict[str, object]]:
    title = str(chapter.get("title") or "Topic").strip()
    objective = str(chapter.get("objective") or title).strip()
    lang = (runtime or "python").strip() or "python"
    tasks: list[dict[str, object]] = []
    levels = ("easy", "medium", "hard")
    for index in range(max(0, min(count, 3))):
        level = levels[index % 3]
        tasks.append(
            {
                "id": _slug(f"{topic_key}-code-t{index + 1}")[:96],
                "kind": "code",
                "title": f"Practice ({level}): {title}"[:120],
                "content": (
                    f"Given: a small {lang} snippet related to {objective}. "
                    f"Expected: working code that demonstrates {objective}. "
                    f"Constraints: keep the solution short; difficulty {level}."
                ),
                "template": (
                    '"""Starter — replace pass with a working solution."""\n'
                    "\n"
                    "def solve() -> str:\n"
                    "    pass\n"
                    "\n"
                    'if __name__ == "__main__":\n'
                    "    print(solve())\n"
                ),
                "tests": [],
                "checker": "llm",
                "rubric": f"Solution demonstrates: {objective[:200]}",
                "level": level,
            }
        )
    return tasks


def _term_is_usable(token: str) -> bool:
    key = token.casefold()
    if len(token) < 4 or key in _STOP:
        return False
    if _WEAK_TERM_RE.fullmatch(token):
        return False
    if re.search(r"[A-Za-z_]", token):
        return True
    # Кириллические термины — только «именные» куски ≥5 букв без глагольных хвостов.
    return len(token) >= 5 and not _WEAK_TERM_RE.search(token)


def _terms_from(blob: str) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in [*_HOOK_RE.findall(blob), *sorted(content_tokens(blob), key=len, reverse=True)]:
        token = raw.strip("/{}")
        key = token.casefold()
        if key in seen or not _term_is_usable(token):
            continue
        seen.add(key)
        ordered.append(token)
        if len(ordered) >= 8:
            break
    return ordered


def _chapter_terms(chapter: dict[str, str], theory: str) -> list[str]:
    title = str(chapter.get("title") or "")
    objective = str(chapter.get("objective") or "")
    ordered: list[str] = []
    seen: set[str] = set()

    for token in [*_terms_from(f"{title} {objective}"), *_terms_from(theory)]:
        key = token.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(token)
        if len(ordered) >= 8:
            break
    if ordered:
        return ordered
    return [(title or objective or "topic").strip()[:40] or "topic"]


def _theory_claims(theory: str) -> list[str]:
    chunks = re.split(r"(?<=[.!?…])\s+|\n+", theory or "")
    claims: list[str] = []
    for raw in chunks:
        text = " ".join(raw.split()).strip()
        if 36 <= len(text) <= 220:
            claims.append(text)
        if len(claims) >= 12:
            break
    return claims


def _place_correct_choice(choices: list[str], *, salt: str) -> tuple[list[str], int]:

    if len(choices) < 2:
        return choices, 0
    target = sum(ord(ch) for ch in salt) % len(choices)
    if target == 0:
        return choices, 0
    out = list(choices)
    out[0], out[target] = out[target], out[0]
    return out, target


def _stem_text(*, ru: bool, term: str, index: int) -> str:
    if ru:
        variants = (
            f"Какое утверждение о «{term}» согласуется с разобранным материалом?",
            f"Что из перечисленного верно про {term}?",
            f"Какой эффект даёт {term} в разобранном примере?",
        )
    else:
        variants = (
            f"Which statement about «{term}» matches the material above?",
            f"Which of the following is true about {term}?",
            f"What effect does {term} have in the example discussed?",
        )
    return variants[index % len(variants)]


def _claim_distractors(
    claims: list[str],
    *,
    term: str,
    correct: str,
    index: int,
    other_terms: list[str],
) -> list[str]:

    folded_term = term.casefold()
    pool = [
        claim
        for claim in claims
        if folded_term not in claim.casefold()
        and claim != correct
        and claim not in correct
        and correct not in claim
    ]
    rotated = pool[index % len(pool) :] + pool[: index % len(pool)] if pool else []
    picked: list[str] = []
    for claim in rotated:
        trimmed = claim[:150]
        if any(_claims_overlap(trimmed, kept) for kept in picked):
            continue
        picked.append(trimmed)
        if len(picked) == 3:
            return picked
    known = {claim.casefold() for claim in claims}
    for swapped in _term_swaps(correct, term=term, other_terms=other_terms):
        if swapped.casefold() in known or swapped in picked:
            continue
        picked.append(swapped[:150])
        if len(picked) == 3:
            return picked
    return picked if len(picked) == 3 else []


def _term_swaps(correct: str, *, term: str, other_terms: list[str]) -> list[str]:

    pattern = re.compile(re.escape(term), re.IGNORECASE)
    swaps: list[str] = []
    for other in other_terms:
        if other.casefold() == term.casefold():
            continue
        candidate = pattern.sub(other, correct)
        if candidate != correct:
            swaps.append(candidate)
    return swaps


def _claims_overlap(first: str, second: str) -> bool:
    left = content_tokens(first)
    right = content_tokens(second)
    if not left or not right:
        return False
    return len(left & right) / len(left | right) >= 0.5


def _quiz_stem_choices(
    locale: str,
    term: str,
    index: int,
    *,
    theory: str = "",
    other_terms: list[str] | None = None,
) -> tuple[str, list[str]]:
    ru = normalize_course_locale(locale) == "ru"
    claims = _theory_claims(theory)
    about_term = [claim for claim in claims if term.casefold() in claim.casefold()]
    if not about_term:
        return "", []
    correct = about_term[index % len(about_term)]
    distractors = _claim_distractors(
        claims,
        term=term,
        correct=correct,
        index=index,
        other_terms=other_terms or [],
    )
    if not distractors:
        return "", []
    question = _stem_text(ru=ru, term=term, index=index)
    return question, [correct[:150], *distractors]


def quizzes_from_chapter_theory(
    *,
    chapter: dict[str, str],
    theory: str,
    count: int,
    topic_key: str,
    locale: str,
    start_index: int = 1,
    already: list[str] | None = None,
) -> list[dict[str, object]]:

    ground = (theory or "").strip() or " ".join(
        part for part in (chapter.get("title"), chapter.get("objective")) if part
    ).strip()
    terms = _chapter_terms(chapter, theory)
    ru = normalize_course_locale(locale) == "ru"
    seen = {item.strip().casefold() for item in (already or []) if item.strip()}
    quizzes: list[dict[str, object]] = []
    probe = 0

    budget = max(count, 1) * 8 + len(terms) * 6
    while len(quizzes) < max(0, count) and probe < budget:
        term = terms[probe % len(terms)]
        question, choices = _quiz_stem_choices(
            locale,
            term,
            probe,
            theory=ground,
            other_terms=terms,
        )
        probe += 1
        if not question or len(choices) < 4:
            continue
        folded = question.casefold()
        if folded in seen:
            continue
        placed, answer = _place_correct_choice(choices, salt=f"{topic_key}:{question}")
        quiz: dict[str, object] = {
            "id": _slug(f"{topic_key}-quiz-g{start_index + len(quizzes)}")[:96],
            "kind": "quiz",
            "generation": "compiled",
            "title": (f"Проверка: {term}" if ru else f"Check: {term}")[:120],
            "question": question[:400],
            "choices": placed,
            "answer": answer,
        }
        if not quiz_item_is_usable(quiz, theory=ground, locale=locale):
            continue
        seen.add(folded)
        quizzes.append(quiz)
    return quizzes


def _java_class_name(fn: str, term: str) -> str:
    parts = re.findall(r"[A-Za-z][A-Za-z0-9]*", f"{fn} {term}")
    if not parts:
        return "ChapterStep"
    return "".join(part[:1].upper() + part[1:] for part in parts[:4])[:48] or "ChapterStep"


def _completion_marker(*, runtime: str, indent: str, term: str) -> list[str]:
    lang = runtime.casefold()
    if lang.startswith(("javascript", "typescript", "java", "go")):
        return [f"{indent}// TODO: допиши шаг про {term}"]
    if lang.startswith(("sql", "sqlite")):
        return [f"{indent}-- TODO: допиши шаг про {term}"]
    return [f"{indent}# TODO: допиши шаг про {term}", f"{indent}..."]


def _fallback_skeleton(*, runtime: str, fn: str, term: str) -> str:
    lang = runtime.casefold()
    if lang == "java":
        class_name = _java_class_name(fn, term)
        return (
            f"public class {class_name} {{\n"
            f"    // TODO: закрепи шаг главы про {term}\n"
            f"    public static void main(String[] args) {{\n"
            f"    }}\n"
            f"}}\n"
        )
    if lang.startswith(("javascript", "typescript")):
        return f"function {fn}(payload) {{\n  // TODO: закрепи шаг главы про {term}\n}}\n"
    if lang.startswith("go"):
        return (
            "package main\n\n"
            f"func {fn}(payload string) string {{\n"
            f"    // TODO: закрепи шаг главы про {term}\n"
            '    return ""\n'
            "}\n"
        )
    if lang.startswith(("sql", "sqlite")):
        return f"-- TODO: закрепи шаг главы про {term}\nSELECT NULL AS result;\n"
    if lang.startswith(("bash", "shell", "sh", "zsh")):
        return f"#!/usr/bin/env bash\n# TODO: закрепи шаг главы про {term}\n"
    if lang.startswith(("python", "py")):
        return f"def {fn}(payload):\n    # TODO: закрепи шаг главы про {term}\n    ...\n"
    return f"TODO: закрепи шаг главы про {term}\nINPUT -> TRANSFORM -> OUTPUT\n"


def _skeleton_from_theory(theory: str, *, fn: str, term: str, runtime: str) -> str:
    lang = (runtime or "python").casefold()
    recovered = starter_from_brief(theory)
    if (
        recovered
        and not starter_is_blank(recovered)
        and starter_matches_runtime(recovered, runtime)
    ):
        lines = recovered.strip().splitlines()
        kept: list[str] = []
        for line in lines[:28]:
            stripped = line.strip()
            if stripped.startswith(("return ", "raise ", "print(", "System.out")):
                break
            kept.append(line.rstrip())
            if re.match(r"^(async\s+)?def\s+\w+", stripped) or stripped.startswith(
                ("class ", "public class")
            ):
                indent = "    "
                kept.extend(_completion_marker(runtime=lang, indent=indent, term=term))
                return "\n".join(kept)[:800]

        if len(kept) >= 4:
            head = kept[: max(2, len(kept) - 2)]
            indent = "    " if any(line.startswith((" ", "\t")) for line in kept) else ""
            head.extend(_completion_marker(runtime=lang, indent=indent, term=term))
            joined = "\n".join(head)
            if starter_matches_runtime(joined, runtime):
                return joined[:800]
        if kept and starter_matches_runtime("\n".join(kept), runtime):
            return "\n".join(kept)[:800]
    return _fallback_skeleton(runtime=lang, fn=fn, term=term)


def practice_from_chapter_theory(
    *,
    chapter: dict[str, str],
    theory: str,
    count: int,
    topic_key: str,
    locale: str,
    runtime: str = "python",
    start_index: int = 1,
) -> list[dict[str, object]]:

    terms = _chapter_terms(chapter, theory)
    claims = _theory_claims(theory)
    chapter_title = str(chapter.get("title") or "Topic").strip() or "Topic"
    ru = normalize_course_locale(locale) == "ru"
    tasks: list[dict[str, object]] = []
    seen_titles: set[str] = set()
    for offset in range(max(0, count)):
        term = terms[offset % len(terms)]
        claim = claims[offset % len(claims)] if claims else ""
        claim_snip = (claim[:72] + ("…" if len(claim) > 72 else "")) if claim else ""
        fn = starter_function_name(f"{chapter_title} {term}")
        if fn == "task":
            fn = "chapter_step"
        if ru:
            title_candidates = (
                f"{chapter_title}: закрепи {term}",
                f"Сценарий с {term}" + (f" — {claim_snip}" if claim_snip else ""),
                f"Практика «{chapter_title}»: {term}",
            )
            content = (
                f"Допиши starter по главе «{chapter_title}»: закрепи работу с {term}. "
                + (
                    f"Опора на утверждение: «{claim[:160]}». "
                    if claim
                    else "Опирайся только на теорию этой главы. "
                )
                + "Без нового API и без GUI."
            )
        else:
            title_candidates = (
                f"{chapter_title}: lock in {term}",
                f"Scenario with {term}" + (f" — {claim_snip}" if claim_snip else ""),
                f"Practice «{chapter_title}»: {term}",
            )
            content = (
                f"Finish the starter for «{chapter_title}»: lock in how {term} works. "
                + (
                    f"Ground it in: «{claim[:160]}». "
                    if claim
                    else "Use only this chapter's theory. "
                )
                + "No new APIs, no GUI."
            )
        title = title_candidates[0][:120]
        for candidate in title_candidates:
            folded = candidate.casefold()
            if folded not in seen_titles:
                title = candidate[:120]
                break
        seen_titles.add(title.casefold())
        task: dict[str, object] = {
            "id": _slug(f"{topic_key}-code-g{start_index + offset}")[:96],
            "kind": "code",
            "title": title,
            "content": content,
            "template": _skeleton_from_theory(theory, fn=fn, term=term, runtime=runtime),
            "tests": [],
            "checker": "llm",
            "rubric": content[:240],
            "level": ("easy", "medium", "hard")[offset % 3],
            "runtime": runtime,
        }
        if practice_spec_is_usable(task, locale=locale, theory=theory, runtime=runtime):
            tasks.append(task)
    return tasks
