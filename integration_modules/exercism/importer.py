from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import NamedTuple, TypedDict

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


class ExercismExercise(TypedDict, total=False):
    slug: str
    title: str
    blurb: str
    type: str


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
    matched: list[dict[str, object]] = []
    for item in list_catalog():
        title = str(item.get("title") or "").casefold()
        description = str(item.get("description") or "").casefold()
        tags_raw = item.get("tags")
        tags: list[object] = list(tags_raw) if isinstance(tags_raw, list) else []
        tag_hit = any(isinstance(tag, str) and needle in tag.casefold() for tag in tags)
        if needle in title or needle in description or tag_hit:
            matched.append(item)
    return matched


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
    track_meta, exercises = _fetch_track_exercises(track_slug)
    title = str(track_meta.get("title") or track_slug)
    selected = [
        exercise
        for raw in exercises[:_MAX_IMPORT_EXERCISES]
        if (exercise := _coerce_exercism_exercise(raw)) is not None
    ]
    enriched = _enrich_exercises_parallel(track_slug, selected)
    steps, study_ids, practice_ids, full_count, partial_count, warnings = _build_track_steps(
        track_slug, selected, enriched
    )
    if not practice_ids:
        raise ValueError(f"exercism track {track_slug} has no importable exercises")
    pack = _track_pack(
        track_slug,
        title=title,
        steps=steps,
        study_ids=study_ids,
        practice_ids=practice_ids,
    )
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


def _fetch_track_exercises(
    track_slug: str,
) -> tuple[dict[str, object], list[object]]:
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
    return track_meta, exercises


class _BuiltExercise(NamedTuple):
    introduction: dict[str, object] | None
    practice: dict[str, object]
    fidelity: str
    warning: dict[str, str] | None


def _build_track_steps(
    track_slug: str,
    exercises: list[ExercismExercise],
    enriched: dict[str, dict[str, str]],
) -> tuple[
    dict[str, dict[str, object]],
    list[str],
    list[str],
    int,
    int,
    list[dict[str, str]],
]:
    runtime = _RUNTIME_BY_TRACK.get(track_slug, "python")
    steps: dict[str, dict[str, object]] = {}
    practice_ids: list[str] = []
    study_ids: list[str] = []
    warnings: list[dict[str, str]] = []
    full_count = 0
    partial_count = 0
    for exercise in exercises:
        slug = str(exercise.get("slug") or "").strip()
        if not slug:
            continue
        built = _build_exercise(exercise, enriched.get(slug) or {}, runtime=runtime)
        if built.introduction is not None:
            intro_id = f"{slug}-intro"
            steps[intro_id] = built.introduction
            study_ids.append(intro_id)
            full_count += 1
        steps[slug] = built.practice
        practice_ids.append(slug)
        if built.fidelity == "full":
            full_count += 1
        else:
            partial_count += 1
        if built.warning is not None:
            warnings.append(built.warning)
    return steps, study_ids, practice_ids, full_count, partial_count, warnings


def _build_exercise(
    exercise: ExercismExercise,
    remote: dict[str, str],
    *,
    runtime: str,
) -> _BuiltExercise:
    slug = str(exercise.get("slug") or "").strip()
    title = str(exercise.get("title") or slug)
    blurb = str(exercise.get("blurb") or "").strip()
    exercise_type = str(exercise.get("type") or "practice").strip() or "practice"
    instructions = str(remote.get("instructions") or "").strip()
    introduction = str(remote.get("introduction") or "").strip()
    template = str(remote.get("template") or "").strip()
    test_source = str(remote.get("test_source") or "").strip()
    source_url = str(remote.get("source_url") or "").strip()
    introduction_step = (
        _introduction_step(slug, title, introduction, source_url) if introduction else None
    )
    practice_docs = _exercise_docs(
        title,
        instructions=instructions,
        introduction=introduction,
        blurb=blurb,
        test_source=test_source,
    )
    fidelity = "full" if (instructions or introduction or blurb) and template else "partial"
    payload: dict[str, object] = {
        "runtime": runtime,
        "runtime_version": "3.12" if runtime == "python" else "latest",
        "template": template or _default_template(runtime, title),
        "instructions": practice_docs,
        "body_md": practice_docs,
        "tests": [],
        "external_step_id": slug,
        "exercism_type": exercise_type,
    }
    for key in ("source_url", "test_source", "solution_file", "test_file"):
        value = str(remote.get(key) or "").strip()
        if value:
            payload[key] = value
    practice = {
        "id": slug,
        "kind": "code",
        "title": title,
        "phase": "practice",
        "fidelity": fidelity,
        "payload": payload,
    }
    warning = (
        None
        if fidelity == "full"
        else {"step": slug, "reason": "github exercise files incomplete; scaffold used"}
    )
    return _BuiltExercise(introduction_step, practice, fidelity, warning)


def _introduction_step(
    slug: str,
    title: str,
    introduction: str,
    source_url: str,
) -> dict[str, object]:
    return {
        "id": f"{slug}-intro",
        "kind": "theory",
        "title": f"{title} — Introduction",
        "phase": "study",
        "fidelity": "full",
        "payload": {
            "instructions": introduction,
            "body_md": introduction,
            "source_url": source_url,
        },
    }


def _exercise_docs(
    title: str,
    *,
    instructions: str,
    introduction: str,
    blurb: str,
    test_source: str,
) -> str:
    docs = instructions or blurb or f"Exercism exercise: {title}"
    if not instructions and introduction and not blurb:
        docs = (
            f"Implement the solution for **{title}**.\n\n"
            "See the Introduction step for the full problem statement."
        )
    if test_source:
        docs = f"{docs.rstrip()}\n\n## Official tests\n\n```\n{test_source.strip()}\n```"
    return docs


def _track_pack(
    track_slug: str,
    *,
    title: str,
    steps: dict[str, dict[str, object]],
    study_ids: list[str],
    practice_ids: list[str],
) -> dict[str, object]:
    return {
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


def _coerce_exercism_exercise(raw: object) -> ExercismExercise | None:
    if not isinstance(raw, dict):
        return None
    exercise: ExercismExercise = {}
    slug = raw.get("slug")
    if isinstance(slug, str) and slug.strip():
        exercise["slug"] = slug.strip()
    title = raw.get("title")
    if isinstance(title, str):
        exercise["title"] = title
    blurb = raw.get("blurb")
    if isinstance(blurb, str):
        exercise["blurb"] = blurb
    exercise_type = raw.get("type")
    if isinstance(exercise_type, str):
        exercise["type"] = exercise_type
    return exercise if exercise.get("slug") else None


def _enrich_exercises_parallel(
    track_slug: str,
    exercises: list[ExercismExercise],
) -> dict[str, dict[str, str]]:
    results: dict[str, dict[str, str]] = {}

    def _one(exercise: ExercismExercise) -> tuple[str, dict[str, str]]:
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
        meta = _exercise_meta(base)
        if meta is None:
            continue
        instructions = _http_text(f"{base}/.docs/instructions.md") or ""
        introduction = _http_text(f"{base}/.docs/introduction.md") or ""
        append = _http_text(f"{base}/.docs/instructions.append.md") or ""
        if append:
            instructions = (
                f"{instructions.rstrip()}\n\n{append.lstrip()}" if instructions else append
            )
        solution_files, test_files = _exercise_files(meta)
        template, solution_file = _first_exercise_file(base, solution_files)
        test_source, test_file = _first_exercise_file(
            base,
            test_files,
            skip_meta=False,
        )
        blurb = str(meta.get("blurb") or "").strip()
        if not instructions and blurb:
            instructions = blurb
        return _github_exercise_payload(
            track,
            slug,
            ref=ref,
            instructions=instructions,
            introduction=introduction,
            template=template,
            test_source=test_source,
            solution_file=solution_file,
            test_file=test_file,
        )
    other = "concept" if kind == "practice" else "practice"
    if other != kind:
        return _fetch_github_exercise_once(track, other, slug)
    return {}


def _fetch_github_exercise_once(track: str, kind: str, slug: str) -> dict[str, str]:
    for ref in _GITHUB_REFS:
        base = _RAW_GITHUB.format(track=track, ref=ref, kind=kind, slug=slug)
        meta = _exercise_meta(base)
        if meta is None:
            continue
        instructions = _http_text(f"{base}/.docs/instructions.md") or ""
        introduction = _http_text(f"{base}/.docs/introduction.md") or ""
        solution_files, _test_files = _exercise_files(meta)
        template, solution_file = _first_exercise_file(base, solution_files)
        return _github_exercise_payload(
            track,
            slug,
            ref=ref,
            instructions=instructions,
            introduction=introduction,
            template=template,
            test_source="",
            solution_file=solution_file,
            test_file="",
        )
    return {}


def _exercise_meta(base: str) -> dict[str, object] | None:
    config = _http_text(f"{base}/.meta/config.json")
    if config is None:
        return None
    try:
        meta = json.loads(config)
    except json.JSONDecodeError:
        return {}
    return meta if isinstance(meta, dict) else {}


def _exercise_files(meta: dict[str, object]) -> tuple[list[object], list[object]]:
    files_raw = meta.get("files")
    files: dict[str, object] = files_raw if isinstance(files_raw, dict) else {}
    solution_raw = files.get("solution")
    test_raw = files.get("test")
    solution_files = list(solution_raw) if isinstance(solution_raw, list) else []
    test_files = list(test_raw) if isinstance(test_raw, list) else []
    return solution_files, test_files


def _first_exercise_file(
    base: str,
    files: list[object],
    *,
    skip_meta: bool = True,
) -> tuple[str, str]:
    for relative in files:
        if not isinstance(relative, str) or not relative.strip():
            continue
        if skip_meta and relative.startswith(".meta/"):
            continue
        content = _http_text(f"{base}/{relative.lstrip('/')}")
        if content is not None:
            return content, relative.strip()
    return "", ""


def _github_exercise_payload(
    track: str,
    slug: str,
    *,
    ref: str,
    instructions: str,
    introduction: str,
    template: str,
    test_source: str,
    solution_file: str,
    test_file: str,
) -> dict[str, str]:
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


def _http_text(url: str) -> str | None:
    try:
        with httpx.Client(
            timeout=_HTTP_TIMEOUT,
            follow_redirects=True,
            headers=_headers(),
        ) as client:
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
        return (
            f"// {title}\nexport function solve() {{\n  throw new Error('Not implemented');\n}}\n"
        )
    if runtime == "go":
        return f'// {title}\npackage main\n\nfunc Solve() string {{\n\treturn ""\n}}\n'
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
