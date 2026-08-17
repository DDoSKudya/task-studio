from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.domain.course_build import CourseBuildStore
from app.domain.course_from_article.local_course.content.messages import (
    order_system_prompt,
    order_user_message,
    practice_system_prompt,
    practice_user_message,
    quiz_system_prompt,
    quiz_user_message,
    theory_system_prompt,
    theory_window_user_message,
)
from app.domain.course_from_article.local_course.curriculum.inventory import TopicSeed
from app.domain.course_from_article.local_course.curriculum.outline import normalize_local_chapters

from .roles import MIN_GOLD_PAIRS, AdapterRefused, AdapterRole, parse_role


@dataclass(frozen=True, slots=True)
class GoldPair:
    role: AdapterRole
    system: str
    user: str
    assistant: str
    build_id: str = ""
    source: str = "local"

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "system": self.system,
            "user": self.user,
            "assistant": self.assistant,
            "build_id": self.build_id,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> GoldPair | None:
        role = parse_role(str(raw.get("role") or ""))
        system = str(raw.get("system") or "").strip()
        user = str(raw.get("user") or "").strip()
        assistant = str(raw.get("assistant") or "").strip()
        if role is None or not system or not user or not assistant:
            return None
        return cls(
            role=role,
            system=system,
            user=user,
            assistant=assistant,
            build_id=str(raw.get("build_id") or ""),
            source=str(raw.get("source") or "local"),
        )


class GoldStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, role: AdapterRole) -> Path:
        return self.root / f"{role}.jsonl"

    def append(self, pair: GoldPair) -> None:
        path = self._path(pair.role)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(pair.to_dict(), ensure_ascii=False) + "\n")

    def load(self, role: AdapterRole) -> list[GoldPair]:
        path = self._path(role)
        if not path.is_file():
            return []
        pairs: list[GoldPair] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(raw, dict):
                continue
            pair = GoldPair.from_dict(raw)
            if pair is not None:
                pairs.append(pair)
        return pairs

    def count(self, role: AdapterRole) -> int:
        return len(self.load(role))


def assert_gold_ready(
    store: GoldStore,
    role: AdapterRole,
    *,
    min_pairs: int | None = None,
) -> int:
    need = MIN_GOLD_PAIRS[role] if min_pairs is None else min_pairs
    got = store.count(role)
    if got < need:
        raise AdapterRefused(f"gold for {role} has {got} pairs, need at least {need}")
    return got


def _locale_from_request(store: CourseBuildStore, user_id: uuid.UUID, build_id: uuid.UUID) -> str:
    try:
        request = store.load_request(user_id, build_id)
    except (OSError, ValueError, json.JSONDecodeError):
        return "ru"
    locale = str(request.get("locale") or "").strip()
    return locale or "ru"


def _chapters_from_build(
    store: CourseBuildStore,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
) -> tuple[list[dict[str, str]], list[str], list[dict[str, str]]]:
    saved = store.load_compiler(user_id, build_id) or store.load_analyze(user_id, build_id)
    if not isinstance(saved, dict):
        return [], [], []
    chapters = normalize_local_chapters(saved.get("chapters"), max_chapters=100)
    raw_outcomes = saved.get("outcomes")
    outcomes = (
        [str(item).strip() for item in raw_outcomes if str(item).strip()]
        if isinstance(raw_outcomes, list)
        else []
    )
    inventory_raw = saved.get("inventory")
    inventory: list[dict[str, str]] = []
    if isinstance(inventory_raw, list):
        for item in inventory_raw:
            if not isinstance(item, dict):
                continue
            if not (title := str(item.get("title") or "").strip()):
                continue
            inventory.append(
                {
                    "title": title,
                    "objective": str(item.get("objective") or title),
                    "excerpt": str(item.get("excerpt") or ""),
                }
            )
    return chapters, outcomes, inventory


def _map_pair(
    *,
    chapters: list[dict[str, str]],
    outcomes: list[str],
    inventory: list[dict[str, str]],
    locale: str,
    build_id: str,
) -> GoldPair | None:
    rows = inventory or [
        {
            "title": item["title"],
            "objective": item.get("objective") or item["title"],
            "excerpt": item.get("source_excerpt") or "",
        }
        for item in chapters
    ]
    if len(rows) < 2:
        return None
    seeds = [
        TopicSeed(
            title=item["title"],
            objective=item["objective"],
            excerpt=item["excerpt"],
            source_title="",
            order=index,
        )
        for index, item in enumerate(rows)
    ]
    title_to_id = {seed.title: str(index) for index, seed in enumerate(seeds)}
    order = [title_to_id[item["title"]] for item in chapters if item["title"] in title_to_id] or [
        str(index) for index in range(len(seeds))
    ]
    assistant = json.dumps({"order": order, "outcomes": outcomes[:6]}, ensure_ascii=False)
    return GoldPair(
        role="course-map",
        system=order_system_prompt(),
        user=order_user_message(seeds, locale=locale),
        assistant=assistant,
        build_id=build_id,
    )


def _topic_pairs(
    payload: dict[str, object],
    *,
    locale: str,
    build_id: str,
) -> list[GoldPair]:
    theories = payload.get("theories")
    theory_steps = (
        [item for item in theories if isinstance(item, dict)] if isinstance(theories, list) else []
    )
    if not theory_steps:
        step = payload.get("theory")
        if isinstance(step, dict):
            theory_steps = [step]
    theory = theory_steps[0] if theory_steps else {}
    title = str(theory.get("title") or payload.get("chapter_id") or "Topic")
    content = str(theory.get("content") or "").strip()
    excerpt = str(theory.get("source_excerpt") or content)
    objective = str(theory.get("objective") or title)
    pairs: list[GoldPair] = []
    if content:
        pairs.append(
            GoldPair(
                role="course-theory",
                system=theory_system_prompt(locale),
                user=theory_window_user_message(
                    locale=locale,
                    title=title,
                    objective=objective,
                    excerpt=excerpt[:9000],
                    window_index=1,
                    window_count=1,
                    prior_digest="",
                ),
                assistant=content,
                build_id=build_id,
            )
        )
    quizzes = payload.get("quizzes")
    if (
        content
        and isinstance(quizzes, list)
        and (usable := [item for item in quizzes if isinstance(item, dict)])
    ):
        pairs.append(
            GoldPair(
                role="course-quiz",
                system=quiz_system_prompt(locale),
                user=quiz_user_message(
                    locale=locale,
                    chunk=len(usable),
                    title=title,
                    objective=objective,
                    theory=content,
                    already=[],
                ),
                assistant=json.dumps({"quizzes": usable}, ensure_ascii=False),
                build_id=build_id,
            )
        )
    codes = payload.get("codes")
    if (
        content
        and isinstance(codes, list)
        and (usable_codes := [item for item in codes if isinstance(item, dict)])
    ):
        pairs.append(
            GoldPair(
                role="course-practice",
                system=practice_system_prompt(locale),
                user=practice_user_message(
                    locale=locale,
                    runtime="python",
                    runtime_version="",
                    chunk=len(usable_codes),
                    title=title,
                    objective=objective,
                    theory=content,
                    already=[],
                ),
                assistant=json.dumps({"tasks": usable_codes}, ensure_ascii=False),
                build_id=build_id,
            )
        )
    return pairs


def harvest_from_build(
    store: CourseBuildStore,
    gold: GoldStore,
    *,
    user_id: uuid.UUID,
    build_id: uuid.UUID,
    source: str = "local",
) -> int:
    locale = _locale_from_request(store, user_id, build_id)
    build_key = str(build_id)
    written = 0
    chapters, outcomes, inventory = _chapters_from_build(store, user_id, build_id)
    mapped = _map_pair(
        chapters=chapters,
        outcomes=outcomes,
        inventory=inventory,
        locale=locale,
        build_id=build_key,
    )
    if mapped is not None:
        gold.append(
            GoldPair(
                role=mapped.role,
                system=mapped.system,
                user=mapped.user,
                assistant=mapped.assistant,
                build_id=mapped.build_id,
                source=source,
            )
        )
        written += 1
    for chapter_id in sorted(store.list_topic_ids(user_id, build_id)):
        payload = store.load_topic(user_id, build_id, chapter_id)
        if not isinstance(payload, dict):
            continue
        for pair in _topic_pairs(payload, locale=locale, build_id=build_key):
            gold.append(
                GoldPair(
                    role=pair.role,
                    system=pair.system,
                    user=pair.user,
                    assistant=pair.assistant,
                    build_id=pair.build_id,
                    source=source,
                )
            )
            written += 1
    return written
