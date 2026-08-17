from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.domain.course_from_article.common.content.textutil import _as_str, _slug


def _code_step_tests_executable(step: dict[str, object]) -> bool:
    if _as_str(step.get("checker")) == "llm":
        return False
    tests = step.get("tests")
    if not isinstance(tests, list) or not tests:
        return False
    runtime = (_as_str(step.get("runtime")) or "python").casefold()
    if runtime not in {
        "python",
        "python3",
        "javascript",
        "js",
        "node",
        "typescript",
        "go",
        "golang",
        "sql",
        "sqlite3",
        "bash",
    }:
        return False
    has_setup = bool(_as_str(step.get("setup")))
    for item in tests:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("run"), str) and str(item["run"]).strip():
            continue
        args = item.get("input")
        if not isinstance(args, list):
            return False
        for value in args:
            if isinstance(value, dict) and "$call" in value and not has_setup:
                return False
            if isinstance(value, str):
                token = value.strip().casefold()
                if (
                    token.startswith("mock_")
                    or token
                    in {
                        "mock_session",
                        "session",
                        "mock",
                        "db",
                        "conn",
                    }
                ) and not has_setup:
                    return False
    return True


def _infer_python_entrypoint(template: str) -> str:
    match = re.search(r"^def\s+([A-Za-z_][\w]*)\s*\(", template, flags=re.MULTILINE)
    return match[1] if match else ""


def _split_steps_evenly(
    steps: list[dict[str, object]],
    *,
    buckets: int,
) -> list[list[dict[str, object]]]:
    if buckets <= 0:
        return []
    if not steps:
        return [[] for _ in range(buckets)]
    chunk_size = max(1, len(steps) // buckets)
    groups: list[list[dict[str, object]]] = []
    cursor = 0
    for index in range(buckets):
        if index == buckets - 1:
            groups.append(steps[cursor:])
        else:
            groups.append(steps[cursor : cursor + chunk_size])
            cursor += chunk_size
    return groups


def _topic_keys(chapters: list[dict[str, str]]) -> list[str]:
    keys: list[str] = []
    seen: dict[str, int] = {}
    for index, chapter in enumerate(chapters or [{"id": "main", "title": "main"}]):
        base = (
            _slug(chapter.get("id") or chapter.get("title") or f"topic-{index + 1}")[:40]
            or f"topic-{index + 1}"
        )
        count = seen.get(base, 0) + 1
        seen[base] = count
        if count == 1:
            keys.append(base)
            continue
        suffix = f"-{count}"
        keys.append(f"{base[: max(1, 40 - len(suffix))]}{suffix}")
    return keys


def align_chapter_ids_to_topic_keys(chapters: list[dict[str, str]]) -> list[dict[str, str]]:
    if not chapters:
        return []
    keys = _topic_keys(chapters)
    return [{**chapter, "id": keys[index]} for index, chapter in enumerate(chapters)]


def _chapter_id_index_map(chapters: list[dict[str, str]]) -> dict[str, int]:
    chapter_list = chapters or [{"id": "main", "title": "main"}]
    topic_keys = _topic_keys(chapter_list)
    mapping: dict[str, int] = {}
    for index, chapter in enumerate(chapter_list):
        mapping[topic_keys[index]] = index
        raw_id = str(chapter.get("id") or "").strip()
        if raw_id and raw_id not in mapping:
            mapping[raw_id] = index
        slug = (
            _slug(raw_id or chapter.get("title") or f"topic-{index + 1}")[:40]
            or f"topic-{index + 1}"
        )
        if slug == topic_keys[index] and slug not in mapping:
            mapping[slug] = index
    return mapping


def _assign_missing_chapter_ids(
    steps: list[dict[str, object]],
    *,
    chapters: list[dict[str, str]],
) -> None:
    if not chapters:
        return
    cursor = 0
    for step in steps:
        if step.get("chapter_id"):
            continue
        step["chapter_id"] = chapters[cursor % len(chapters)]["id"]
        cursor += 1


def _group_steps_by_chapter(
    steps: list[dict[str, object]],
    *,
    chapters: list[dict[str, str]],
) -> list[list[dict[str, object]]]:
    chapter_list = chapters or [{"id": "main", "title": "main"}]
    topic_count = max(1, len(chapter_list))
    id_to_index = _chapter_id_index_map(chapter_list)
    groups: list[list[dict[str, object]]] = [[] for _ in range(topic_count)]
    orphans: list[dict[str, object]] = []
    for step in steps:
        raw = step.get("chapter_id")
        if not raw:
            orphans.append(step)
            continue
        key = str(raw).strip()
        index = id_to_index.get(key)
        if index is None:
            index = id_to_index.get(_slug(key)[:40])
        if index is None:
            orphans.append(step)
        else:
            groups[index].append(step)
    if orphans:
        for index, group in enumerate(_split_steps_evenly(orphans, buckets=topic_count)):
            groups[index].extend(group)
    return groups


def _put_steps_without_chapter(
    all_steps: dict[str, object],
    steps: list[dict[str, object]],
) -> list[str]:
    ids: list[str] = []
    for step in steps:
        step_id = str(step["id"])
        if step_id in all_steps:
            suffix = 2
            while f"{step_id}-{suffix}" in all_steps:
                suffix += 1
            step_id = f"{step_id}-{suffix}"
        ids.append(step_id)
        all_steps[step_id] = {
            key: value for key, value in step.items() if key not in {"id", "chapter_id"}
        }
    return ids


def _video_title_blob(video: dict[str, object]) -> str:
    return " ".join(
        part
        for part in (
            _as_str(video.get("title")),
            _as_str(video.get("source_title")),
            _as_str(video.get("chapter_id")),
        )
        if part
    ).casefold()


def _best_chapter_for_video(
    video: dict[str, object],
    chapters: list[dict[str, str]],
) -> int | None:
    blob = _video_title_blob(video)
    if not blob or not chapters:
        return None
    best_index = None
    best_score = 0.42
    for index, chapter in enumerate(chapters):
        title = (_as_str(chapter.get("title")) or "").casefold()
        if not title:
            continue
        if title in blob or blob in title:
            return index

        cleaned = re.sub(r"\s*[—\-–]\s*video\s*\d+\s*$", "", blob).strip()
        score = SequenceMatcher(None, cleaned, title).ratio()
        if score > best_score:
            best_score = score
            best_index = index
    return best_index


def _videos_by_chapter(
    videos: list[dict[str, object]],
    chapters: list[dict[str, str]],
) -> list[list[dict[str, object]]]:

    buckets: list[list[dict[str, object]]] = [[] for _ in chapters] or [[]]
    unmatched: list[dict[str, object]] = []
    for video in videos:
        index = _best_chapter_for_video(video, chapters)
        if index is None:
            unmatched.append(video)
        else:
            buckets[index].append(video)
    if unmatched:
        buckets[0].extend(unmatched)
    return buckets


def _assemble_interleaved_manifest(
    *,
    pack_id: str,
    title: str,
    locale: str,
    runtime: str,
    runtime_version: str,
    chapters: list[dict[str, str]],
    theory_steps: list[dict[str, object]],
    quiz_steps: list[dict[str, object]],
    code_steps: list[dict[str, object]],
    video_steps: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    videos = video_steps or []
    chapter_list = chapters or [{"id": "main", "title": title}]
    _assign_missing_chapter_ids(theory_steps, chapters=chapter_list)
    _assign_missing_chapter_ids(quiz_steps, chapters=chapter_list)
    _assign_missing_chapter_ids(code_steps, chapters=chapter_list)
    theory_groups = _group_steps_by_chapter(theory_steps, chapters=chapter_list)
    quiz_groups = _group_steps_by_chapter(quiz_steps, chapters=chapter_list)
    code_groups = _group_steps_by_chapter(code_steps, chapters=chapter_list)
    video_groups = _videos_by_chapter(videos, chapter_list)
    topic_ids = _topic_keys(chapter_list)

    all_steps: dict[str, object] = {}
    topics: list[dict[str, object]] = []

    for index, chapter in enumerate(chapter_list):
        topic_theory = theory_groups[index] if index < len(theory_groups) else []
        topic_quizzes = quiz_groups[index] if index < len(quiz_groups) else []
        topic_codes = code_groups[index] if index < len(code_groups) else []
        topic_videos = video_groups[index] if index < len(video_groups) else []
        if topic_videos and topic_theory:
            ordered_study = [topic_theory[0], *topic_videos, *topic_theory[1:]]
        else:
            ordered_study = [*topic_theory, *topic_videos]
        topics.append(
            {
                "id": topic_ids[index],
                "title": _as_str(chapter.get("title")) or f"Topic {index + 1}",
                "phases": {
                    "study": {"steps": _put_steps_without_chapter(all_steps, ordered_study)},
                    "assess": {"steps": _put_steps_without_chapter(all_steps, topic_quizzes)},
                    "practice": {"steps": _put_steps_without_chapter(all_steps, topic_codes)},
                },
            }
        )

    return {
        "schema_version": 1,
        "id": pack_id,
        "title": title,
        "version": "1.0.0",
        "locale": locale,
        "source": {"type": "local"},
        "defaults": {"runtime": runtime, "runtime_version": runtime_version},
        "policies": {
            "skip_study_allowed": True,
            "assess_without_practice": True,
            "phase_order": ["study", "assess", "practice"],
            "assess": {"max_attempts": 3, "autocomplete": False},
            "tutor_enabled": True,
        },
        "topics": topics,
        "steps": all_steps,
    }


def _assemble_manifest(
    *,
    pack_id: str,
    title: str,
    locale: str,
    runtime: str,
    runtime_version: str,
    theory_steps: list[dict[str, object]],
    quiz_steps: list[dict[str, object]],
    code_steps: list[dict[str, object]],
    video_steps: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    videos = video_steps or []

    if theory_steps and videos:
        ordered_study = [theory_steps[0], *videos, *theory_steps[1:]]
    else:
        ordered_study = [*theory_steps, *videos]
    steps: dict[str, object] = {}
    study_ids = _put_steps_without_chapter(steps, ordered_study)
    practice_ids = _put_steps_without_chapter(steps, code_steps)
    assess_ids = _put_steps_without_chapter(steps, quiz_steps)
    topic_id = _slug(pack_id)[:40] or "main"
    return {
        "schema_version": 1,
        "id": pack_id,
        "version": "1.0.0",
        "title": title,
        "locale": locale,
        "source": {"type": "local"},
        "defaults": {"runtime": runtime, "runtime_version": runtime_version},
        "policies": {
            "skip_study_allowed": True,
            "assess_without_practice": True,
            "phase_order": ["study", "assess", "practice"],
            "assess": {"max_attempts": 3, "autocomplete": False},
            "tutor_enabled": True,
        },
        "topics": [
            {
                "id": topic_id,
                "title": title,
                "phases": {
                    "study": {"steps": study_ids},
                    "practice": {"steps": practice_ids},
                    "assess": {"steps": assess_ids},
                },
            }
        ],
        "steps": steps,
    }


def _repair_manifest_shapes(manifest: dict[str, object]) -> dict[str, object]:
    topics = manifest.get("topics")
    if not isinstance(topics, list):
        return manifest
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        phases = topic.get("phases")
        if not isinstance(phases, dict):
            continue
        for phase_name in ("study", "practice", "assess"):
            value = phases.get(phase_name)
            if isinstance(value, list):
                phases[phase_name] = {"steps": [str(item) for item in value]}
            elif isinstance(value, dict) and "steps" not in value:
                phases[phase_name] = {"steps": []}
    return manifest
