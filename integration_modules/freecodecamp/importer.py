from __future__ import annotations

import html
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import httpx

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_PLATFORM = "freecodecamp"
_GRAPHQL = "https://curriculum-db.freecodecamp.org/graphql"
_PAGE_DATA = "https://www.freecodecamp.org/page-data/learn/{superblock}/{block}/{challenge}/page-data.json"
_HTTP_TIMEOUT = httpx.Timeout(45.0, connect=15.0)
_MAX_BLOCKS = 24
_MAX_CHALLENGES = 80
_FETCH_WORKERS = 8

_TITLE_OVERRIDES: dict[str, str] = {
    "responsive-web-design": "Responsive Web Design",
    "javascript-algorithms-and-data-structures": "JavaScript Algorithms and Data Structures",
    "front-end-development-libraries": "Front End Development Libraries",
    "data-visualization": "Data Visualization",
    "back-end-development-and-apis": "Back End Development and APIs",
    "quality-assurance": "Quality Assurance",
    "scientific-computing-with-python": "Scientific Computing with Python",
    "data-analysis-with-python": "Data Analysis with Python",
    "information-security": "Information Security",
    "coding-interview-prep": "Coding Interview Prep",
    "machine-learning-with-python": "Machine Learning with Python",
    "relational-databases": "Relational Databases",
    "python-for-everybody": "Python for Everybody",
    "full-stack-developer": "Full Stack Developer",
    "javascript-algorithms-and-data-structures-22": (
        "JavaScript Algorithms and Data Structures (New)"
    ),
    "responsive-web-design-22": "Responsive Web Design (New)",
}


_CODE_TYPES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18, 20, 25, 26, 27, 28, 29}


def health() -> dict[str, object]:
    return {"status": "ok", "platform": _PLATFORM}


def list_catalog(**_ctx: object) -> list[dict[str, object]]:
    try:
        payload = _graphql("{ curriculum { superblocks } }")
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        raise ValueError(f"freecodecamp catalog failed: {detail}") from exc

    curriculum = payload.get("curriculum")
    if not isinstance(curriculum, dict):
        return []
    superblocks = curriculum.get("superblocks")
    if not isinstance(superblocks, list):
        return []

    catalog: list[dict[str, object]] = []
    for raw in superblocks:
        slug = str(raw).strip()
        if not slug or slug.endswith("-v9") or slug in {"dev-playground", "the-odin-project"}:
            continue
        catalog.append(
            {
                "id": slug,
                "platform": _PLATFORM,
                "external_id": slug,
                "title": _title_for(slug),
                "description": f"freeCodeCamp certification path · {slug}",
                "author": "freeCodeCamp",
                "language": "en",
                "tags": _tags_for(slug),
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
        external_id = str(item.get("external_id") or "").casefold()
        tags_raw = item.get("tags")
        tags: list[object] = list(tags_raw) if isinstance(tags_raw, list) else []
        tag_hit = any(isinstance(tag, str) and needle in tag.casefold() for tag in tags)
        if needle in title or needle in description or needle in external_id or tag_hit:
            matched.append(item)
    return matched


def import_course(*, course_id: str, **_ctx: object) -> tuple[dict[str, object], dict[str, object]]:
    slug = course_id.strip()
    if not slug:
        raise ValueError("freecodecamp superblock id required")

    if slug in {"1", "course_1"} and (_FIXTURES / "course_1.json").is_file():
        payload = json.loads((_FIXTURES / "course_1.json").read_text(encoding="utf-8"))
        pack = {
            **payload,
            "platform": _PLATFORM,
            "external_id": slug,
            "slug": f"fcc-{slug}",
            "title": str(payload.get("title") or _title_for(slug)),
        }
        return pack, _report(pack)

    try:
        payload = _graphql(
            """
            query ($slug: String!) {
              superblock(dashedName: $slug) {
                name
                dashedName
                blocks
                blockObjects {
                  name
                  dashedName
                  challengeOrder { id title }
                }
              }
            }
            """,
            variables={"slug": slug},
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"freecodecamp fetch failed: {exc}") from exc

    superblock = payload.get("superblock")
    if not isinstance(superblock, dict):
        raise ValueError(f"freecodecamp superblock {slug!r} not found")

    title = str(superblock.get("name") or _title_for(slug))
    block_objects = superblock.get("blockObjects")
    blocks = block_objects if isinstance(block_objects, list) else []
    if not blocks:
        block_names = superblock.get("blocks")
        if isinstance(block_names, list):
            blocks = [
                {"dashedName": name, "name": _title_for(str(name)), "challengeOrder": []}
                for name in block_names
            ]

    topics: list[dict[str, object]] = []
    steps: dict[str, dict[str, object]] = {}
    imported = 0
    warnings: list[dict[str, str]] = []
    limited_blocks = blocks[:_MAX_BLOCKS]
    fetch_jobs: list[tuple[str, str, str, str, str]] = []

    for block in limited_blocks:
        if not isinstance(block, dict):
            continue
        block_slug = str(block.get("dashedName") or "").strip()
        if not block_slug:
            continue
        block_title = str(block.get("name") or _title_for(block_slug))
        challenges = block.get("challengeOrder")
        challenge_rows = challenges if isinstance(challenges, list) else []

        overview_id = f"block-{block_slug}"
        steps[overview_id] = {
            "id": overview_id,
            "kind": "theory",
            "title": block_title,
            "phase": "study",
            "fidelity": "partial",
            "payload": {
                "body_html": (
                    f"<h1>{html.escape(block_title)}</h1>"
                    f"<p>Section from freeCodeCamp "
                    f"<code>{html.escape(slug)}</code> / "
                    f"<code>{html.escape(block_slug)}</code>.</p>"
                ),
                "instructions": (
                    f"# {block_title}\n\n"
                    f"Section from freeCodeCamp `{slug}` / `{block_slug}`."
                ),
            },
        }
        study_ids = [overview_id]
        practice_ids: list[str] = []
        imported += 1

        for challenge in challenge_rows:
            if imported >= _MAX_CHALLENGES:
                break
            if not isinstance(challenge, dict):
                continue
            challenge_id = str(challenge.get("id") or "").strip()
            challenge_title = str(challenge.get("title") or challenge_id).strip()
            if not challenge_id or not challenge_title:
                continue
            step_id = f"ch-{challenge_id}"
            dashed = _dashed_name(challenge_title)
            fetch_jobs.append((step_id, challenge_id, challenge_title, block_slug, dashed))
            steps[step_id] = _scaffold_challenge(
                step_id=step_id,
                title=challenge_title,
                block_slug=block_slug,
                superblock=slug,
            )
            practice_ids.append(step_id)
            imported += 1

        topics.append(
            {
                "id": f"topic-{block_slug}",
                "title": block_title,
                "study": study_ids,
                "practice": practice_ids,
                "assess": [],
            }
        )
        if imported >= _MAX_CHALLENGES:
            break

    if not topics or not steps:
        raise ValueError(f"freecodecamp superblock {slug!r} has no importable content")

    challenge_payloads = _fetch_challenges_parallel(slug, fetch_jobs)
    for step_id, challenge_id, challenge_title, block_slug, dashed in fetch_jobs:
        remote = challenge_payloads.get(step_id)
        if not remote:
            warnings.append(
                {
                    "step": step_id,
                    "reason": f"page-data missing for {block_slug}/{dashed}",
                }
            )
            continue
        mapped, _fidelity, warning = _map_challenge(
            step_id=step_id,
            challenge_id=challenge_id,
            title=challenge_title,
            block_slug=block_slug,
            superblock=slug,
            remote=remote,
        )
        steps[step_id] = mapped
        if warning:
            warnings.append({"step": step_id, "reason": warning})

    full_count = sum(1 for step in steps.values() if step.get("fidelity") == "full")
    partial_count = len(steps) - full_count

    pack = {
        "platform": _PLATFORM,
        "external_id": slug,
        "title": f"freeCodeCamp — {title}",
        "slug": f"fcc-{slug}",
        "version": "1.0.0",
        "locale": "en",
        "topics": topics,
        "steps": steps,
        "course_assess": [],
    }
    if not warnings:
        warnings.append(
            {
                "step": "course",
                "reason": (
                    "FCC browser/DOM asserts stay on freecodecamp.org; "
                    "simple JS asserts and starter files are imported for local checks"
                ),
            }
        )
    report = {
        "total_items": len(steps),
        "imported_full": full_count,
        "imported_partial": partial_count,
        "skipped": max(0, len(blocks) - len(limited_blocks)),
        "warnings": warnings[:40],
    }
    return pack, report


def _fetch_challenges_parallel(
    superblock: str,
    jobs: list[tuple[str, str, str, str, str]],
) -> dict[str, dict[str, object]]:
    if not jobs:
        return {}

    results: dict[str, dict[str, object]] = {}

    def _one(job: tuple[str, str, str, str, str]) -> tuple[str, dict[str, object] | None]:
        step_id, _cid, _title, block_slug, dashed = job
        url = _PAGE_DATA.format(
            superblock=quote(superblock, safe="-"),
            block=quote(block_slug, safe="-"),
            challenge=quote(dashed, safe="-"),
        )
        try:
            with httpx.Client(
                timeout=_HTTP_TIMEOUT,
                follow_redirects=True,
                headers=_headers(),
            ) as client:
                response = client.get(url)
                if response.status_code != 200:
                    return step_id, None
                payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError):
            return step_id, None
        node: object | None = None
        if isinstance(payload, dict):
            result = payload.get("result")
            data = result.get("data") if isinstance(result, dict) else None
            challenge_node = data.get("challengeNode") if isinstance(data, dict) else None
            node = (
                challenge_node.get("challenge")
                if isinstance(challenge_node, dict)
                else None
            )
        if not isinstance(node, dict):
            return step_id, None
        return step_id, node

    workers = min(_FETCH_WORKERS, max(1, len(jobs)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_one, job) for job in jobs]
        for future in as_completed(futures):
            step_id, node = future.result()
            if node is not None:
                results[step_id] = node
    return results


def _map_challenge(
    *,
    step_id: str,
    challenge_id: str,
    title: str,
    block_slug: str,
    superblock: str,
    remote: dict[str, object],
) -> tuple[dict[str, object], str, str | None]:
    description = _as_html(remote.get("description"))
    instructions = _as_html(remote.get("instructions"))
    tests_raw_obj = remote.get("tests")
    tests_raw: list[object] = list(tests_raw_obj) if isinstance(tests_raw_obj, list) else []
    files_raw_obj = remote.get("challengeFiles")
    files_raw: list[object] = list(files_raw_obj) if isinstance(files_raw_obj, list) else []
    files: list[dict[str, object]] = [
        item for item in files_raw if isinstance(item, dict)
    ]
    questions_obj = remote.get("questions")
    questions: list[object] = list(questions_obj) if isinstance(questions_obj, list) else []
    video_id = str(remote.get("videoId") or "").strip()
    video_url = str(remote.get("videoUrl") or "").strip()
    if video_id and not video_url:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
    help_category = str(remote.get("helpCategory") or "")
    challenge_type = _as_int(remote.get("challengeType"))

    body_html = _compose_body_html(
        description=description,
        instructions=instructions,
        tests=tests_raw,
        video_url=video_url if questions else "",
    )
    source_url = (
        f"https://www.freecodecamp.org/learn/{superblock}/{block_slug}/"
        f"{_dashed_name(title)}"
    )

    quiz = _quiz_from_questions(questions)
    if quiz is not None:
        payload: dict[str, object] = {
            **quiz,
            "body_html": body_html or description or instructions,
            "instructions": _html_to_text(body_html or description or instructions or title),
            "source_url": source_url,
            "external_step_id": challenge_id,
            "fcc_challenge_type": challenge_type,
        }
        if video_url:
            payload["video_url"] = video_url
        fidelity = "full" if quiz.get("choices") and "answer" in quiz else "partial"
        warning = None if fidelity == "full" else "quiz answer key incomplete"
        return (
            {
                "id": step_id,
                "kind": "quiz",
                "title": title,
                "phase": "practice",
                "fidelity": fidelity,
                "payload": payload,
            },
            fidelity,
            warning,
        )

    if video_url and not files:
        fidelity = "full" if description or instructions else "partial"
        return (
            {
                "id": step_id,
                "kind": "video",
                "title": title,
                "phase": "study",
                "fidelity": fidelity,
                "payload": {
                    "video_url": video_url,
                    "body_html": body_html or description,
                    "instructions": _html_to_text(body_html or description or title),
                    "source_url": source_url,
                    "external_step_id": challenge_id,
                    "fcc_challenge_type": challenge_type,
                },
            },
            fidelity,
            None,
        )

    runtime, runtime_version = _runtime_for(superblock, help_category, files)
    template = _template_from_files(files, runtime=runtime)
    has_body = bool(body_html.strip())
    if challenge_type in _CODE_TYPES or files or tests_raw or has_body or template.strip():
        warning: str | None = None
        fidelity = "full" if has_body else "partial"
        if not template.strip():
            template = _default_template(runtime, title)
            warning = (
                "starter file empty; scaffold template used"
                if has_body
                else "challenge body empty"
            )
        else:
            if tests_raw:
                warning = "FCC browser asserts are imported as text only"
            if not has_body:
                warning = "challenge instructions missing"
        return (
            {
                "id": step_id,
                "kind": "code",
                "title": title,
                "phase": "practice",
                "fidelity": fidelity,
                "payload": {
                    "runtime": runtime,
                    "runtime_version": runtime_version,
                    "template": template,
                    "body_html": body_html,
                    "instructions": _html_to_text(body_html) or title,
                    "tests": [],
                    "fcc_tests": _fcc_tests_payload(tests_raw),
                    "source_url": source_url,
                    "external_step_id": challenge_id,
                    "fcc_challenge_type": challenge_type,
                    "fcc_test_count": len(tests_raw),
                },
            },
            fidelity,
            warning,
        )

    fidelity = "full" if body_html.strip() else "partial"
    return (
        {
            "id": step_id,
            "kind": "theory",
            "title": title,
            "phase": "study",
            "fidelity": fidelity,
            "payload": {
                "body_html": body_html or f"<p>{html.escape(title)}</p>",
                "instructions": _html_to_text(body_html) or title,
                "source_url": source_url,
                "external_step_id": challenge_id,
            },
        },
        fidelity,
        None if fidelity == "full" else "challenge body empty",
    )


def _scaffold_challenge(
    *,
    step_id: str,
    title: str,
    block_slug: str,
    superblock: str,
) -> dict[str, object]:
    runtime, runtime_version = _runtime_for(superblock, "", [])
    return {
        "id": step_id,
        "kind": "code",
        "title": title,
        "phase": "practice",
        "fidelity": "partial",
        "payload": {
            "runtime": runtime,
            "runtime_version": runtime_version,
            "template": _default_template(runtime, title),
            "instructions": f"Challenge from freeCodeCamp block `{block_slug}`.",
            "tests": [],
        },
    }


def _compose_body_html(
    *,
    description: str,
    instructions: str,
    tests: list[object],
    video_url: str = "",
) -> str:
    parts: list[str] = []
    if video_url:
        parts.append(
            f'<p><a href="{html.escape(video_url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">Watch lesson video</a></p>'
        )
    if description.strip():
        parts.append(description.strip())
    if instructions.strip():
        parts.append(instructions.strip())
    test_items: list[str] = []
    for item in tests:
        if not isinstance(item, dict):
            continue
        text = _as_html(item.get("text"))
        if text.strip():
            test_items.append(f"<li>{text}</li>")
    if test_items:
        parts.append("<h3>Tests</h3><ul>" + "".join(test_items) + "</ul>")
    return "\n".join(parts)


def _fcc_tests_payload(tests: list[object]) -> list[dict[str, str]]:
    payload: list[dict[str, str]] = []
    for item in tests:
        if not isinstance(item, dict):
            continue
        text = _as_html(item.get("text"))
        test_string = item.get("testString")
        if not isinstance(test_string, str) or not test_string.strip():
            continue
        payload.append(
            {
                "text": _html_to_text(text),
                "test_string": test_string.strip(),
            }
        )
    return payload


def _quiz_from_questions(questions: list[object]) -> dict[str, object] | None:
    for item in questions:
        if not isinstance(item, dict):
            continue
        question = _html_to_text(_as_html(item.get("text")))
        answers = item.get("answers")
        if not isinstance(answers, list) or not answers:
            continue
        choices: list[str] = []
        for answer in answers:
            if isinstance(answer, dict):
                choices.append(_html_to_text(_as_html(answer.get("answer"))))
            elif isinstance(answer, str):
                choices.append(_html_to_text(answer))
        choices = [choice for choice in choices if choice]
        if not question or not choices:
            continue
        payload: dict[str, object] = {"question": question, "choices": choices}
        solution = _as_int(item.get("solution"))
        if solution is not None and 1 <= solution <= len(choices):
            payload["answer"] = solution - 1
        return payload
    return None


def _template_from_files(files: list[dict[str, object]], *, runtime: str) -> str:
    if not files:
        return ""
    chunks: list[str] = []
    comment = "#" if runtime in {"python", "sql", "ruby"} else "//"
    for item in files:
        contents = item.get("contents")
        if not isinstance(contents, str):
            contents = ""
        name = str(item.get("name") or "file")
        ext = str(item.get("ext") or "")
        label = f"{name}.{ext}" if ext else name
        if len(files) > 1:
            chunks.append(f"{comment} --- {label} ---\n{contents}".rstrip())
        else:
            chunks.append(contents.rstrip())
    return "\n\n".join(chunk for chunk in chunks if chunk).strip()


def _runtime_for(
    superblock: str,
    help_category: str,
    files: list[dict[str, object]],
) -> tuple[str, str]:
    haystack = f"{superblock} {help_category}".casefold()
    exts = {str(item.get("ext") or "").casefold() for item in files}
    if "py" in exts or "python" in haystack:
        return "python", "3.12"
    if "sql" in exts or "sql" in haystack or "database" in haystack:
        return "sql", "15"
    if "ts" in exts or "tsx" in exts:
        return "javascript", "22"
    return "javascript", "22"


def _default_template(runtime: str, title: str) -> str:
    if runtime == "python":
        return f"# {title}\ndef solution():\n    raise NotImplementedError\n"
    if runtime == "sql":
        return f"-- {title}\nSELECT 1;\n"
    return f"// {title}\nfunction solution() {{\n  return null;\n}}\n"


def _dashed_name(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")


def _as_html(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _html_to_text(value: str) -> str:
    if not value:
        return ""
    text = re.sub(r"(?i)<br\s*/?>", "\n", value)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = re.sub(r"(?i)</li>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _graphql(query: str, *, variables: dict[str, object] | None = None) -> dict[str, object]:
    body: dict[str, object] = {"query": query}
    if variables:
        body["variables"] = variables
    with httpx.Client(timeout=_HTTP_TIMEOUT, headers=_headers()) as client:
        response = client.post(_GRAPHQL, json=body)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("invalid graphql response")
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict):
            raise ValueError(str(first.get("message") or first))
        raise ValueError(str(first))
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("graphql response missing data")
    return data


def _headers() -> dict[str, str]:
    return {"User-Agent": "task-studio-importer/1.0", "Accept": "application/json"}


def _title_for(slug: str) -> str:
    if slug in _TITLE_OVERRIDES:
        return _TITLE_OVERRIDES[slug]
    return re.sub(r"[-_]+", " ", slug).strip().title()


def _tags_for(slug: str) -> list[str]:
    tags = ["freeCodeCamp"]
    lowered = slug.casefold()
    if "python" in lowered:
        tags.append("Python")
    if "javascript" in lowered or "js" in lowered:
        tags.append("JavaScript")
    if "html" in lowered or "web-design" in lowered or "front-end" in lowered:
        tags.append("Web")
    if "sql" in lowered or "database" in lowered:
        tags.append("SQL")
    if "data" in lowered:
        tags.append("Data")
    return tags


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
