from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import httpx

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_PLATFORM = "exercism"
_API = "https://exercism.org/api/v2"
_RAW_GITHUB = "https://raw.githubusercontent.com/exercism/{track}/{ref}/exercises/{kind}/{slug}"
_HTTP_TIMEOUT = httpx.Timeout(45.0, connect=15.0)
_MAX_IMPORT_EXERCISES = 60
_FETCH_WORKERS = 8
_GITHUB_REFS = ("main", "master")

_RUNTIME_BY_TRACK: dict[str, str] = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "javascript",
    "go": "go",
    "java": "java",
    "rust": "rust",
    "csharp": "csharp",
    "cpp": "cpp",
    "c": "c",
    "ruby": "ruby",
    "elixir": "elixir",
    "sql": "sql",
}


def health() -> dict[str, object]:
    return {"status": "ok", "platform": _PLATFORM}


def list_catalog(**_ctx: object) -> list[dict[str, object]]:
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, headers=_headers()) as client:
            response = client.get(f"{_API}/tracks")
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        raise ValueError(f"exercism catalog failed: {detail}") from exc

    tracks = payload.get("tracks")
    if not isinstance(tracks, list):
        return []

    catalog: list[dict[str, object]] = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        slug = str(track.get("slug") or "").strip()
        if not slug:
            continue
        title = str(track.get("title") or slug)
        num_exercises = track.get("num_exercises")
        exercise_count = num_exercises if isinstance(num_exercises, int) else 0
        tags_raw = track.get("tags")
        tags = (
            [str(tag) for tag in tags_raw if isinstance(tag, str) and tag.strip()][:8]
            if isinstance(tags_raw, list)
            else []
        )
        catalog.append(
            {
                "platform": _PLATFORM,
                "external_id": slug,
                "title": title,
                "description": f"{exercise_count} exercises",
                "author": "Exercism",
                "language": title,
                "tags": tags,
            }
        )
    return sorted(catalog, key=lambda item: str(item["title"]).casefold())


def search_remote(*, query: str, **_ctx: object) -> list[dict[str, object]]:
    needle = query.casefold().strip()
    if not needle:
        return []
    return [
        item
        for item in list_catalog()
        if needle in str(item["title"]).casefold()
        or needle in str(item.get("description", "")).casefold()
        or any(
            needle in str(tag).casefold()
            for tag in (item.get("tags") if isinstance(item.get("tags"), list) else [])
            if isinstance(tag, str)
        )
    ]


def import_course(*, course_id: str, **_ctx: object) -> tuple[dict[str, object], dict[str, object]]:
    track_slug = course_id.strip()
    if not track_slug:
        raise ValueError("exercism track slug required")

    try:
        return _import_live_track(track_slug)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        if track_slug == "1" and _fixture_exists():
            return _import_fixture()
        detail = str(exc).strip() or exc.__class__.__name__
        raise ValueError(f"exercism import failed for track {track_slug}: {detail}") from exc


def _import_live_track(track_slug: str) -> tuple[dict[str, object], dict[str, object]]:
    with httpx.Client(timeout=_HTTP_TIMEOUT, headers=_headers()) as client:
        track_response = client.get(f"{_API}/tracks")
        track_response.raise_for_status()
        tracks_payload = track_response.json()
        tracks = tracks_payload.get("tracks")
        if not isinstance(tracks, list):
            raise ValueError("invalid tracks payload")

        track_meta = next(
            (item for item in tracks if isinstance(item, dict) and item.get("slug") == track_slug),
            None,
        )
        if not track_meta:
            raise ValueError(f"exercism track {track_slug} not found")

        exercises_response = client.get(f"{_API}/tracks/{track_slug}/exercises")
        exercises_response.raise_for_status()
        exercises_payload = exercises_response.json()

    exercises = exercises_payload.get("exercises")
    if not isinstance(exercises, list) or not exercises:
        raise ValueError(f"exercism track {track_slug} has no exercises")

    title = str(track_meta.get("title") or track_slug)
    runtime = _RUNTIME_BY_TRACK.get(track_slug, "python")
    selected = [item for item in exercises[:_MAX_IMPORT_EXERCISES] if isinstance(item, dict)]
    enriched = _enrich_exercises_parallel(track_slug, selected)

    steps: dict[str, dict[str, object]] = {}
    practice_ids: list[str] = []
    study_ids: list[str] = []
    warnings: list[dict[str, str]] = []
    full_count = 0
    partial_count = 0

    for exercise in selected:
        slug = str(exercise.get("slug") or "").strip()
        if not slug:
            continue
        step_title = str(exercise.get("title") or slug)
        blurb = str(exercise.get("blurb") or "").strip()
        exercise_type = str(exercise.get("type") or "practice").strip() or "practice"
        remote = enriched.get(slug) or {}

        instructions = str(remote.get("instructions") or "").strip()
        introduction = str(remote.get("introduction") or "").strip()
        template = str(remote.get("template") or "").strip()
        test_source = str(remote.get("test_source") or "").strip()
        solution_file = str(remote.get("solution_file") or "").strip()
        test_file = str(remote.get("test_file") or "").strip()
        source_url = str(remote.get("source_url") or "").strip()

        if introduction:
            intro_id = f"{slug}-intro"
            steps[intro_id] = {
                "id": intro_id,
                "kind": "theory",
                "title": f"{step_title} — Introduction",
                "phase": "study",
                "fidelity": "full",
                "payload": {
                    "instructions": introduction,
                    "body_md": introduction,
                    "source_url": source_url,
                },
            }
            study_ids.append(intro_id)
            full_count += 1

                                                                                     
        practice_docs = instructions or blurb or f"Exercism exercise: {step_title}"
        if not instructions and introduction and not blurb:
            practice_docs = (
                f"Implement the solution for **{step_title}**.\n\n"
                "See the Introduction step for the full problem statement."
            )
        if test_source:
            practice_docs = (
                f"{practice_docs.rstrip()}\n\n## Official tests\n\n"
                f"```\n{test_source.strip()}\n```"
            )

        has_docs = bool(instructions or introduction or blurb)
        has_template = bool(template)
        fidelity = "full" if has_docs and has_template else "partial"
        if not has_template:
            template = _default_template(runtime, step_title)

        payload: dict[str, object] = {
            "runtime": runtime,
            "runtime_version": "3.12" if runtime == "python" else "latest",
            "template": template,
            "instructions": practice_docs,
            "body_md": practice_docs,
            "tests": [],
            "external_step_id": slug,
            "exercism_type": exercise_type,
        }
        if source_url:
            payload["source_url"] = source_url
        if test_source:
            payload["test_source"] = test_source
        if solution_file:
            payload["solution_file"] = solution_file
        if test_file:
            payload["test_file"] = test_file

        steps[slug] = {
            "id": slug,
            "kind": "code",
            "title": step_title,
            "phase": "practice",
            "fidelity": fidelity,
            "payload": payload,
        }
        practice_ids.append(slug)
        if fidelity == "full":
            full_count += 1
        else:
            partial_count += 1
            warnings.append(
                {
                    "step": slug,
                    "reason": "github exercise files incomplete; scaffold used",
                }
            )

    if not practice_ids:
        raise ValueError(f"exercism track {track_slug} has no importable exercises")

    pack = {
        "platform": _PLATFORM,
        "external_id": track_slug,
        "title": f"Exercism — {title}",
        "slug": f"exercism-{track_slug}",
        "version": "1.0.0",
        "locale": "en",
        "topics": [
            {
                "id": "track",
                "title": title,
                "study": study_ids,
                "practice": practice_ids,
                "assess": [],
            }
        ],
        "steps": steps,
        "course_assess": [],
    }
    if not any(item.get("reason", "").startswith("github") for item in warnings):
        warnings.append(
            {
                "step": "course",
                "reason": (
                    "Exercism Python tests run locally via unittest/Piston; "
                    "Jest and other track harnesses are not executed yet"
                ),
            }
        )
    report = {
        "total_items": len(steps),
        "imported_full": full_count,
        "imported_partial": partial_count,
        "skipped": max(0, len(exercises) - len(selected)),
        "warnings": warnings[:40],
    }
    return pack, report


def _enrich_exercises_parallel(
    track_slug: str,
    exercises: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    results: dict[str, dict[str, str]] = {}

    def _one(exercise: dict[str, Any]) -> tuple[str, dict[str, str]]:
        slug = str(exercise.get("slug") or "").strip()
        if not slug:
            return "", {}
        kind = str(exercise.get("type") or "practice").strip() or "practice"
        if kind not in {"practice", "concept"}:
            kind = "practice"
        return slug, _fetch_github_exercise(track_slug, kind, slug)

    workers = min(_FETCH_WORKERS, max(1, len(exercises)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, exercise) for exercise in exercises]
        for future in as_completed(futures):
            slug, payload = future.result()
            if slug:
                results[slug] = payload
    return results


def _fetch_github_exercise(track: str, kind: str, slug: str) -> dict[str, str]:
    for ref in _GITHUB_REFS:
        base = _RAW_GITHUB.format(track=track, ref=ref, kind=kind, slug=slug)
        config = _http_text(f"{base}/.meta/config.json")
        if config is None:
            continue
        try:
            meta = json.loads(config)
        except json.JSONDecodeError:
            meta = {}
        if not isinstance(meta, dict):
            meta = {}

        instructions = _http_text(f"{base}/.docs/instructions.md") or ""
        introduction = _http_text(f"{base}/.docs/introduction.md") or ""
        append = _http_text(f"{base}/.docs/instructions.append.md") or ""
        if append:
            instructions = f"{instructions.rstrip()}\n\n{append.lstrip()}" if instructions else append

        files = meta.get("files") if isinstance(meta.get("files"), dict) else {}
        solution_files = files.get("solution") if isinstance(files.get("solution"), list) else []
        test_files = files.get("test") if isinstance(files.get("test"), list) else []

        template = ""
        solution_file = ""
        for relative in solution_files:
            if not isinstance(relative, str) or not relative.strip():
                continue
            if relative.startswith(".meta/"):
                continue
            content = _http_text(f"{base}/{relative.lstrip('/')}")
            if content is not None:
                template = content
                solution_file = relative.strip()
                break

        test_source = ""
        test_file = ""
        for relative in test_files:
            if not isinstance(relative, str) or not relative.strip():
                continue
            content = _http_text(f"{base}/{relative.lstrip('/')}")
            if content is not None:
                test_source = content
                test_file = relative.strip()
                break

        blurb = str(meta.get("blurb") or "").strip()
        if not instructions and blurb:
            instructions = blurb

        return {
            "instructions": instructions,
            "introduction": introduction,
            "template": template,
            "test_source": test_source,
            "solution_file": solution_file,
            "test_file": test_file,
            "source_url": f"https://exercism.org/tracks/{track}/exercises/{slug}",
            "ref": ref,
        }

                                                                                            
    other = "concept" if kind == "practice" else "practice"
    if other != kind:
        return _fetch_github_exercise_once(track, other, slug)
    return {}


def _fetch_github_exercise_once(track: str, kind: str, slug: str) -> dict[str, str]:
                                                                     
    for ref in _GITHUB_REFS:
        base = _RAW_GITHUB.format(track=track, ref=ref, kind=kind, slug=slug)
        config = _http_text(f"{base}/.meta/config.json")
        if config is None:
            continue
        try:
            meta = json.loads(config)
        except json.JSONDecodeError:
            meta = {}
        files = meta.get("files") if isinstance(meta, dict) and isinstance(meta.get("files"), dict) else {}
        solution_files = files.get("solution") if isinstance(files.get("solution"), list) else []
        instructions = _http_text(f"{base}/.docs/instructions.md") or ""
        introduction = _http_text(f"{base}/.docs/introduction.md") or ""
        template = ""
        solution_file = ""
        for relative in solution_files:
            if isinstance(relative, str) and not relative.startswith(".meta/"):
                content = _http_text(f"{base}/{relative.lstrip('/')}")
                if content is not None:
                    template = content
                    solution_file = relative.strip()
                    break
        return {
            "instructions": instructions,
            "introduction": introduction,
            "template": template,
            "test_source": "",
            "solution_file": solution_file,
            "test_file": "",
            "source_url": f"https://exercism.org/tracks/{track}/exercises/{slug}",
            "ref": ref,
        }
    return {}


def _http_text(url: str) -> str | None:
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True, headers=_headers()) as client:
            response = client.get(url)
            if response.status_code != 200:
                return None
            return response.text
    except httpx.HTTPError:
        return None


def _default_template(runtime: str, title: str) -> str:
    if runtime == "python":
        return f"# {title}\ndef solve():\n    raise NotImplementedError\n"
    if runtime == "javascript":
        return f"// {title}\nexport function solve() {{\n  throw new Error('Not implemented');\n}}\n"
    if runtime == "go":
        return f"// {title}\npackage main\n\nfunc Solve() string {{\n\treturn \"\"\n}}\n"
    if runtime == "sql":
        return f"-- {title}\nSELECT 1;\n"
    return f"// {title}\n"


def _headers() -> dict[str, str]:
    return {"User-Agent": "task-studio-importer/1.0", "Accept": "application/json"}


def _fixture_exists() -> bool:
    return (_FIXTURES / "course_1.json").is_file()


def _import_fixture() -> tuple[dict[str, object], dict[str, object]]:
    payload = _load_fixture()
    pack = {
        **payload,
        "platform": _PLATFORM,
        "external_id": "1",
        "slug": "exercism-1",
    }
    return pack, _report(payload)


def _load_fixture() -> dict[str, object]:
    return json.loads((_FIXTURES / "course_1.json").read_text(encoding="utf-8"))


def _report(payload: dict[str, object]) -> dict[str, object]:
    steps = payload.get("steps", {})
    total = len(steps) if isinstance(steps, dict) else 0
    return {
        "total_items": total,
        "imported_full": total,
        "imported_partial": 0,
        "skipped": 0,
        "warnings": [],
    }
