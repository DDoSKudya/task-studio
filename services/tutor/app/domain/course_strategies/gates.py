from __future__ import annotations

import re

_MD_FRAGMENT = re.compile(r"!\[|\*\*\*|^\s*#")
_AUTHOR_BIO = re.compile(
    r"(меня зовут|my name is|привет[,!]?\s+меня|hi[,!]?\s+i'?m\s)",
    re.IGNORECASE,
)
_LETTER_ONLY = frozenset({"a", "b", "c", "d", "а", "б", "в", "г"})

_PLACEHOLDER_CHOICE_RE = re.compile(
    r"^(?:full\s+text|option|choice|answer|вариант|ответ|текст\s+варианта)"
    r"\s*(?:[a-dа-г]|one|two|three|four|[1-9])?\b",
    re.IGNORECASE,
)
_MANY_ANSWER_MARKERS = (
    "выберите все",
    "выбери все",
    "все правильные",
    "все верные",
    "несколько правильных",
    "несколько верных",
    "select all",
    "choose all",
    "all that apply",
)
_DANGLING_TAIL = re.compile(r"[,;:\-—]$")
_SERVICE_PART_SUFFIX = re.compile(
    r"(?:\s+\((?:part|часть)?\s*\d+\)|\s+(?:part|часть)\s+\d+)\s*$",
    re.IGNORECASE,
)
_TRUNCATED_RU_DERIVATION = re.compile(r"[а-яё]+(?:ац|изац|фикац|ирова)$", re.IGNORECASE)
_DANGLING_ADJ_AFTER_DETERMINER = re.compile(
    r"(?:той\s+же|одной(?:\s+и\s+той\s+же)?|этой|своей|новой)\s+"
    r"\S+(?:ной|ной|ой|ый|ий|ая|ое|ые|ую|юю|ым|им)$",
    re.IGNORECASE,
)
_RU_ADJ_TAIL = (
    "ной",
    "ной",
    "ой",
    "ый",
    "ий",
    "ая",
    "ое",
    "ые",
    "ую",
    "юю",
    "ым",
    "им",
)

_INNER_SENTENCE_BREAK = re.compile(r"\w{3,}[.!?]\s+[^\Wa-zа-яё]", re.UNICODE)
_DISCOURSE_FRAGMENT = re.compile(
    r"^(?:"
    r"также|но\s|мы\s|для этого|обычно|например|сейчас|"
    r"ещ[её] один|конечно|это позволяет|при этом|"
    r"получи(?:те)?\b|давай(?:те)?\b|сделай(?:те)?\b|посмотри(?:те)?\b|"
    r"get\s+a\b|let'?s\b|try\s+this\b"
    r")\b",
    re.IGNORECASE,
)

_TRAILING_FUNCTION_WORD = frozenset(
    {
        "и",
        "а",
        "но",
        "или",
        "либо",
        "же",
        "бы",
        "ли",
        "не",
        "ни",
        "в",
        "во",
        "на",
        "о",
        "об",
        "обо",
        "с",
        "со",
        "к",
        "ко",
        "по",
        "из",
        "за",
        "для",
        "при",
        "от",
        "до",
        "у",
        "над",
        "под",
        "про",
        "через",
        "между",
        "без",
        "перед",
        "это",
        "этот",
        "эта",
        "этой",
        "этом",
        "этих",
        "эти",
        "этого",
        "тот",
        "та",
        "те",
        "того",
        "той",
        "том",
        "тех",
        "свой",
        "своя",
        "своей",
        "своих",
        "его",
        "её",
        "их",
        "как",
        "что",
        "чем",
        "чтобы",
        "если",
        "когда",
        "где",
        "который",
        "которая",
        "которое",
        "которые",
        "одной",
        "одном",
        "одно",
        "одного",
        "одним",
        "одну",
        "эту",
        "помощью",
        "этими",
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "on",
        "at",
        "for",
        "with",
        "and",
        "or",
        "but",
        "that",
        "this",
        "these",
        "those",
        "from",
        "by",
        "as",
        "is",
        "are",
        "was",
        "were",
        "its",
        "their",
        "your",
        "into",
        "onto",
        "about",
        "over",
        "under",
        "than",
        "then",
        "when",
        "which",
        "same",
        "more",
        "most",
        "such",
        "using",
        "via",
        "through",
    }
)


def title_is_sentence_fragment(title: str) -> bool:

    text = " ".join((title or "").split()).strip()
    if not text:
        return True
    if _DANGLING_TAIL.search(text):
        return True
    if _INNER_SENTENCE_BREAK.search(text):
        return True
    if _DISCOURSE_FRAGMENT.search(text):
        return True
    if _ends_on_function_word(text):
        return True
    if _ends_on_dangling_adjective(text):
        return True
    first = text[0]
    return first.isalpha() and first.islower()


def _ends_on_function_word(text: str) -> bool:

    words = text.split()
    if len(words) < 2:
        return False
    last = words[-1].strip(".…»\"'()[]").casefold()
    return last in _TRAILING_FUNCTION_WORD


def _ends_on_dangling_adjective(text: str) -> bool:
    flat = " ".join(text.split())
    if _DANGLING_ADJ_AFTER_DETERMINER.search(flat):
        return True
    words = flat.split()
    if len(words) < 4:
        return False
    last = words[-1].strip(".…»\"'()[]").casefold()
    if not any(last.endswith(suffix) for suffix in _RU_ADJ_TAIL):
        return False
    return ":" not in flat and "—" not in flat and " - " not in flat and len(words) >= 8


def chapter_title_is_valid(title: str) -> bool:
    text = " ".join((title or "").split()).strip()
    if not text or len(text) > 70:
        return False
    if _SERVICE_PART_SUFFIX.search(text) or _TRUNCATED_RU_DERIVATION.search(text):
        return False
    if _MD_FRAGMENT.search(text):
        return False
    if _AUTHOR_BIO.search(text):
        return False
    if title_is_sentence_fragment(text):
        return False
    words = text.split()
    too_long_clause = len(words) >= 10 and ":" not in text and "—" not in text and " - " not in text
    return not too_long_clause


def sanitize_chapter_title(title: str, *, fallback: str = "Topic") -> str:
    text = " ".join((title or "").split()).strip()
    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\*+", "", text)
    text = " ".join(text.split()).strip()
    if chapter_title_is_valid(text):
        return text

    chunk = re.split(r"[.!?]", text, maxsplit=1)[0].strip()
    words = chunk.split()

    for count in range(min(len(words), 10), 2, -1):
        short = " ".join(words[:count]).strip(" ,;:—-")
        if chapter_title_is_valid(short):
            return short
    base_words = " ".join((fallback or "Topic").split()).split()
    base = ""
    for word in base_words:
        candidate = f"{base} {word}".strip()
        if len(candidate) > 70:
            break
        base = candidate
    if chapter_title_is_valid(base):
        return base
    return base or "Topic"


def choices_are_letter_only(choices: object) -> bool:
    if not isinstance(choices, list) or len(choices) < 2:
        return False
    labels = [str(item).strip().casefold() for item in choices]
    if any(not label for label in labels):
        return False
    return all(label in _LETTER_ONLY for label in labels)


def _choice_text_in_question(choice: object, folded_question: str) -> bool:
    if not isinstance(choice, str) or len(choice) <= 15:
        return False
    return " ".join(choice.split()).casefold() in folded_question


def question_embeds_choices(question: str, choices: object) -> bool:

    text = question or ""
    if not isinstance(choices, list) or len(choices) < 2:
        return False
    labelled = re.findall(r"(?:^|\n)\s*(?:[A-Da-dА-Га-г]|[1-9])[).:]\s*\S", text)
    if len(labelled) >= 2:
        return True
    folded = " ".join(text.split()).casefold()
    hits = sum(1 for choice in choices if _choice_text_in_question(choice, folded))
    return hits >= 2


def strip_inline_choice_letters(question: str) -> tuple[str, list[str] | None]:

    text = question or ""
    pattern = re.compile(
        r"(?:^|\n)\s*([A-Da-dА-Га-г])[).\:]\s*(.+?)(?=(?:\n\s*[A-Da-dА-Га-г][).\:])|$)",
        re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    if len(matches) < 2:
        return text.strip(), None
    choices = [" ".join(m.group(2).split()) for m in matches]
    stem = text[: matches[0].start()].strip()
    return stem or text.strip(), choices


def quiz_stem_key(question: str) -> str:

    stem, _ = strip_inline_choice_letters(question or "")
    flat = " ".join(stem.split()).casefold()
    return re.sub(r"[^\w\s]", "", flat, flags=re.UNICODE).strip()


def choice_is_placeholder(choice: object) -> bool:

    text = " ".join(str(choice or "").split()).casefold()
    if not text:
        return True
    return _PLACEHOLDER_CHOICE_RE.match(text) is not None


def stem_wants_many_answers(question: str) -> bool:

    flat = " ".join((question or "").split()).casefold()
    return any(marker in flat for marker in _MANY_ANSWER_MARKERS)


def quiz_stem_tokens(question: str) -> frozenset[str]:
    key = quiz_stem_key(question)
    return frozenset(word for word in key.split() if len(word) > 3)


def quiz_stems_overlap(first: str, second: str) -> float:
    left = quiz_stem_tokens(first)
    right = quiz_stem_tokens(second)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def quizzes_are_near_duplicates(
    first: dict[str, object],
    second: dict[str, object],
    *,
    threshold: float = 0.72,
) -> bool:

    stem_a = str(first.get("question") or "")
    stem_b = str(second.get("question") or "")
    if quiz_stems_overlap(stem_a, stem_b) >= threshold:
        return True
    choices_a = _folded_choice_set(first.get("choices"))
    choices_b = _folded_choice_set(second.get("choices"))
    if not choices_a or choices_a != choices_b:
        return False
    return quiz_stems_overlap(stem_a, stem_b) >= 0.4


def _folded_choice_set(choices: object) -> frozenset[str]:
    if not isinstance(choices, list):
        return frozenset()
    return frozenset(
        " ".join(str(item).split()).casefold() for item in choices if str(item).strip()
    )


def dedupe_quiz_batch(
    quizzes: list[dict[str, object]],
    *,
    threshold: float = 0.72,
) -> list[dict[str, object]]:
    kept: list[dict[str, object]] = []
    for quiz in quizzes:
        if any(quizzes_are_near_duplicates(quiz, earlier, threshold=threshold) for earlier in kept):
            continue
        kept.append(quiz)
    return kept
