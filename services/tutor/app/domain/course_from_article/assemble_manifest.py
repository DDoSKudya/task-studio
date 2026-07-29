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
                                                                            
    study_ids = [str(step["id"]) for step in theory_steps] + [str(step["id"]) for step in videos]
    practice_ids = [str(step["id"]) for step in code_steps]
    assess_ids = [str(step["id"]) for step in quiz_steps]
    steps: dict[str, object] = {}
    for step in [*theory_steps, *videos, *code_steps, *quiz_steps]:
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
