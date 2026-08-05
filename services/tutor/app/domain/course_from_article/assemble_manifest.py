from __future__ import annotations

import re

from .textutil import _as_str, _slug


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


def _group_steps_by_chapter(
    steps: list[dict[str, object]],
    *,
    chapters: list[dict[str, str]],
) -> list[list[dict[str, object]]]:
    topic_count = max(1, len(chapters))
    chapter_ids = [
        _slug(chapter.get("id") or chapter.get("title") or f"topic-{index + 1}")[:40]
        or f"topic-{index + 1}"
        for index, chapter in enumerate(chapters or [{"id": "main", "title": "main"}])
    ]
    id_set = set(chapter_ids)
    buckets: dict[str, list[dict[str, object]]] = {cid: [] for cid in chapter_ids}
    orphans: list[dict[str, object]] = []
    for step in steps:
        raw = step.get("chapter_id")
        cid = _slug(str(raw))[:40] if raw else ""
        if cid and cid in id_set:
            buckets[cid].append(step)
        else:
            orphans.append(step)
    if orphans:
        orphan_groups = _split_steps_evenly(orphans, buckets=topic_count)
        for index, group in enumerate(orphan_groups):
            buckets[chapter_ids[index]].extend(group)
    return [buckets[cid] for cid in chapter_ids]


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
    theory_groups = _group_steps_by_chapter(theory_steps, chapters=chapter_list)
    quiz_groups = _group_steps_by_chapter(quiz_steps, chapters=chapter_list)
    code_groups = _group_steps_by_chapter(code_steps, chapters=chapter_list)

    all_steps: dict[str, object] = {}
    topics: list[dict[str, object]] = []

    for index, chapter in enumerate(chapter_list):
        topic_id = (
            _slug(chapter.get("id") or chapter.get("title") or f"topic-{index + 1}")[:40]
            or f"topic-{index + 1}"
        )
        topic_theory = theory_groups[index] if index < len(theory_groups) else []
        topic_quizzes = quiz_groups[index] if index < len(quiz_groups) else []
        topic_codes = code_groups[index] if index < len(code_groups) else []
        topic_videos = videos if index == 0 else []

        # Video = separate study slides; place after the first theory slide of topic 0
        # so they are not buried after the whole chapter dump.
        if topic_videos and topic_theory:
            ordered_study = [topic_theory[0], *topic_videos, *topic_theory[1:]]
        else:
            ordered_study = [*topic_theory, *topic_videos]
        study_ids = [str(step["id"]) for step in ordered_study]
        assess_ids = [str(step["id"]) for step in topic_quizzes]
        practice_ids = [str(step["id"]) for step in topic_codes]

        for step in [*ordered_study, *topic_quizzes, *topic_codes]:
            step_id = str(step["id"])
            all_steps[step_id] = {
                key: value for key, value in step.items() if key not in {"id", "chapter_id"}
            }

        topics.append(
            {
                "id": topic_id,
                "title": _as_str(chapter.get("title")) or f"Topic {index + 1}",
                "phases": {
                    "study": {"steps": study_ids},
                    "assess": {"steps": assess_ids},
                    "practice": {"steps": practice_ids},
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
    study_ids = [str(step["id"]) for step in ordered_study]
    practice_ids = [str(step["id"]) for step in code_steps]
    assess_ids = [str(step["id"]) for step in quiz_steps]
    steps: dict[str, object] = {}
    for step in [*ordered_study, *code_steps, *quiz_steps]:
        step_id = str(step["id"])
        payload = {key: value for key, value in step.items() if key != "id"}
        steps[step_id] = payload
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
