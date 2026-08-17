from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

ExerciseKind = Literal["quiz", "practice", "open", "answer_key"]

_EXERCISE_HEADING = re.compile(
    r"^(#{1,6})\s+(?P<title>.+)$",
    re.MULTILINE,
)
_EXERCISE_TITLE = re.compile(
    r"(?i)(?:"
    r"задани[еяй]|практическ\w*\s+задани|"
    r"дополнительн\w*\s+практическ|"
    r"проверь(?:те)?\s+себ|"
    r"вопросы?\s+(?:для\s+)?самопровер|"
    r"ответы?\s+на\s+задани|"
    r"\bexercise\b|\bhomework\b|\bquiz\b|"
    r"check\s+yourself|try\s+it(?:\s+yourself)?|"
    r"knowledge\s+check|self[- ]?check|"
    r"what\s+you\s+(?:will\s+)?build|"
    r"your\s+turn"
    r")"
)
_INLINE_EXERCISE = re.compile(
    r"(?im)^(?:\*\*)?(?:задани[ея]\s*\d*|exercise\s*\d*|quiz\s*\d*)(?:\*\*)?\s*[:.\-—]"
)
_CHOICE_MARK = re.compile(r"(?im)^(?:\s*(?:[-*•]|\d+[.)])\s+)?(?:\[[ x]\]|[A-Da-d][).:])\s+\S")
_ANSWER_HEADING = re.compile(r"(?i)ответы?\s+на\s+задани|answer\s*key|correct\s+answers?")


@dataclass(frozen=True)
class HarvestedExercise:
    kind: ExerciseKind
    title: str
    body: str
    source_title: str = ""

    def as_prompt_block(self) -> str:
        return f"### [{self.kind}] {self.title}\n{self.body.strip()}"


@dataclass(frozen=True)
class HarvestResult:
    teaching_markdown: str
    exercises: tuple[HarvestedExercise, ...]

    @property
    def quiz_seeds(self) -> list[HarvestedExercise]:
        return [item for item in self.exercises if item.kind in {"quiz", "open"}]

    @property
    def practice_seeds(self) -> list[HarvestedExercise]:
        return [item for item in self.exercises if item.kind == "practice"]


def harvest_markdown_exercises(
    markdown: str,
    *,
    source_title: str = "",
) -> HarvestResult:
    text = (markdown or "").replace("\r\n", "\n")
    if not text.strip():
        return HarvestResult(teaching_markdown="", exercises=())

    matches = list(_EXERCISE_HEADING.finditer(text))
    if not matches and not _INLINE_EXERCISE.search(text):
        return HarvestResult(teaching_markdown=text, exercises=())

    keep: list[str] = []
    exercises: list[HarvestedExercise] = []
    cursor = 0
    index = 0
    while index < len(matches):
        match = matches[index]
        title = (match.group("title") or "").strip()
        if not _EXERCISE_TITLE.search(title):
            index += 1
            continue

        level = len(match.group(1))
        start = match.start()
        keep.append(text[cursor:start])
        end = len(text)
        for nxt in matches[index + 1 :]:
            nxt_level = len(nxt.group(1))
            nxt_title = (nxt.group("title") or "").strip()
            if nxt_level <= level and not _EXERCISE_TITLE.search(nxt_title):
                end = nxt.start()
                break
            if nxt_level <= level and _EXERCISE_TITLE.search(nxt_title):
                end = nxt.start()
                break
        body = text[match.end() : end].strip()
        exercises.append(
            HarvestedExercise(
                kind=_classify_exercise(title, body),
                title=_clean_title(title),
                body=body[:6_000],
                source_title=source_title,
            )
        )
        cursor = end
        index += 1

    keep.append(text[cursor:])
    teaching = "".join(keep)
    teaching = _strip_inline_exercise_paragraphs(teaching)
    teaching = re.sub(r"\n{3,}", "\n\n", teaching).strip()
    return HarvestResult(teaching_markdown=teaching, exercises=tuple(exercises))


def harvest_sources(
    sources: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[HarvestedExercise]]:
    cleaned: list[dict[str, object]] = []
    seeds: list[HarvestedExercise] = []
    for item in sources:
        title = str(item.get("title") or "")
        content = str(item.get("content") or "")
        result = harvest_markdown_exercises(content, source_title=title)
        next_item = dict(item)
        next_item["content"] = result.teaching_markdown or content
        cleaned.append(next_item)
        seeds.extend(result.exercises)
    return cleaned, seeds


def strip_theory_exercise_sections(markdown: str) -> str:
    result = harvest_markdown_exercises(markdown)
    cleaned = result.teaching_markdown
    cleaned = _strip_inline_exercise_paragraphs(cleaned)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def exercises_to_checkpoint(
    exercises: list[HarvestedExercise] | tuple[HarvestedExercise, ...],
) -> list[dict[str, str]]:
    return [
        {
            "kind": item.kind,
            "title": item.title,
            "body": item.body[:4_000],
            "source_title": item.source_title,
        }
        for item in exercises[:24]
    ]


def exercises_from_checkpoint(raw: object) -> list[HarvestedExercise]:
    if not isinstance(raw, list):
        return []
    out: list[HarvestedExercise] = []
    for item in raw[:24]:
        if not isinstance(item, dict):
            continue
        kind_raw = str(item.get("kind") or "open").strip().lower()
        kind_map: dict[str, ExerciseKind] = {
            "quiz": "quiz",
            "practice": "practice",
            "open": "open",
            "answer_key": "answer_key",
        }
        kind = kind_map.get(kind_raw, "open")
        title = str(item.get("title") or "").strip()
        body = str(item.get("body") or "").strip()
        if not title and not body:
            continue
        out.append(
            HarvestedExercise(
                kind=kind,
                title=title or "Exercise",
                body=body[:6_000],
                source_title=str(item.get("source_title") or ""),
            )
        )
    return out


def _classify_exercise(title: str, body: str) -> ExerciseKind:
    blob = f"{title}\n{body}"
    if _ANSWER_HEADING.search(title) or _ANSWER_HEADING.search(body[:200]):
        return "answer_key"
    choice_hits = len(_CHOICE_MARK.findall(body))
    if choice_hits >= 2 or re.search(r"(?i)\b(выберите|choose|multiple\s+choice)\b", blob):
        return "quiz"
    if re.search(r"```|^\s{0,3}(?:\$|#)\s+\S", body, re.MULTILINE) and re.search(
        r"(?i)(?:создай|напиши|запусти|выполните|implement|write|run\b)",
        blob,
    ):
        return "practice"
    if re.search(r"(?i)практическ\w*\s+задани|lab\b|hands[- ]?on", title):
        return "practice"
    return "open"


def _clean_title(title: str) -> str:
    cleaned = re.sub(r"[*_`]+", "", title).strip()
    return cleaned[:160] or "Exercise"


def _strip_inline_exercise_paragraphs(markdown: str) -> str:
    lines = markdown.split("\n")
    out: list[str] = []
    skipping = False
    for line in lines:
        if _INLINE_EXERCISE.match(line.strip()):
            skipping = True
            continue
        if skipping:
            if not line.strip():
                skipping = False
                out.append(line)
                continue
            if line.startswith("#") or _EXERCISE_HEADING.match(line):
                skipping = False
                out.append(line)
                continue
            continue
        out.append(line)
    return "\n".join(out)
