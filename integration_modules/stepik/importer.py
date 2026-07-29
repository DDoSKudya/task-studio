from __future__ import annotations

import html
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_API = "https://stepik.org/api"
_STEPIK_ORIGIN = "https://stepik.org"
_TOKEN_URL = "https://stepik.org/oauth2/token/"
_HTTP_TIMEOUT = httpx.Timeout(60.0, connect=15.0)
_BATCH_SIZE = 40
_MAX_STEPS = 150
_CATALOG_TEXT_LIMIT = 400
_STEP_TEXT_LIMIT = 50_000
_HTML_LIMIT = 200_000
_ALLOWED_TAGS = frozenset(
    {
        "p",
        "br",
        "hr",
        "div",
        "span",
        "ul",
        "ol",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "pre",
        "code",
        "blockquote",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "a",
        "img",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "sup",
        "sub",
    }
)
_VOID_TAGS = frozenset({"br", "hr", "img"})
_RUNTIME_ALIASES = {
    "python": ("python", "3.12"),
    "python3": ("python", "3.12"),
    "py": ("python", "3.12"),
    "javascript": ("javascript", "20"),
    "js": ("javascript", "20"),
    "typescript": ("typescript", "5.4"),
    "ts": ("typescript", "5.4"),
    "java": ("java", "21"),
    "c": ("c", "17"),
    "cpp": ("cpp", "17"),
    "c++": ("cpp", "17"),
    "go": ("go", "1.22"),
    "rust": ("rust", "1.78"),
    "sql": ("sql", "15"),
}
_TOPIC_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Python", ("python", "поколение python")),
    ("C++", ("c++", "с++", "cpp")),
    ("Java", ("java",)),
    ("JavaScript", ("javascript", "js ")),
    ("Docker", ("docker", "kubernetes", "k8s")),
    ("SQL", ("sql", "баз данных", "database")),
    ("Algorithms", ("алгоритм", "algorithm", "структур данных")),
    ("ML", ("machine learning", "машинн", "data science", "нейросет")),
    ("Security", ("security", "безопасн", "информационн")),
    ("Go", ("golang", " go ")),
)


def health() -> dict[str, object]:
    return {"status": "ok", "platform": "stepik"}


def list_catalog(
    *,
    username: str = "",
    password: str = "",
    client_id: str = "",
    client_secret: str = "",
    **_ctx: object,
) -> list[dict[str, object]]:
\
\
\
\
       
    token = _maybe_access_token(
        username=username,
        password=password,
        client_id=client_id,
        client_secret=client_secret,
    )
    if not token:
                                                                                       
        if username.strip() and password.strip():
            raise ValueError(
                "stepik Client ID required "
                "(set STEPIK_CLIENT_ID on the server or save Client ID in settings)"
            )
        return []
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            enrolled = _api_get(
                client,
                "courses",
                token=token,
                params={"enrolled": "true"},
            )
            return _courses_to_catalog(enrolled.get("courses", []))
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        raise ValueError(f"stepik enrolled catalog failed: {detail}") from exc


def search_remote(
    *,
    query: str,
    username: str = "",
    password: str = "",
    client_id: str = "",
    client_secret: str = "",
    **_ctx: object,
) -> list[dict[str, object]]:
    needle = query.casefold().strip()
    if not needle:
        return []

    by_id: dict[str, dict[str, object]] = {}
    try:
        enrolled = list_catalog(
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
        )
    except ValueError:
        enrolled = []
    for item in enrolled:
        external_id = str(item.get("external_id") or item.get("id") or "")
        if external_id and (
            needle in str(item.get("title", "")).casefold()
            or needle in str(item.get("description", "")).casefold()
            or any(
                needle in str(tag).casefold()
                for tag in (item.get("tags") or [])
                if isinstance(tag, str)
            )
        ):
            by_id[external_id] = item

    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            try:
                token = _maybe_access_token(
                    username=username,
                    password=password,
                    client_id=client_id,
                    client_secret=client_secret,
                )
            except ValueError:
                token = None
            payload = _api_get(
                client,
                "courses",
                token=token,
                params={"page": "1", "search": query.strip()},
            )
            for item in _courses_to_catalog(payload.get("courses", [])):
                external_id = str(item.get("external_id") or item.get("id") or "")
                if external_id:
                    by_id[external_id] = item
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        pass

    return sorted(by_id.values(), key=lambda item: str(item.get("title", "")).casefold())


def import_course(
    *,
    course_id: str,
    username: str = "",
    password: str = "",
    client_id: str = "",
    client_secret: str = "",
    **_ctx: object,
) -> tuple[dict[str, object], dict[str, object]]:
    token = _maybe_access_token(
        username=username,
        password=password,
        client_id=client_id,
        client_secret=client_secret,
    )
    if not token:
        if _fixture_exists(course_id):
            return _import_fixture(course_id)
        msg = (
            "stepik login required: save email/password, Client ID and Client secret "
            "in Settings → Stepik"
        )
        raise ValueError(msg)
    try:
        return _import_live(course_id, token=token)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        if _fixture_exists(course_id):
            return _import_fixture(course_id)
        detail = str(exc).strip() or exc.__class__.__name__
        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {401, 403}:
            msg = (
                f"stepik course {course_id} requires login "
                "(save Stepik email/password in Settings; set STEPIK_CLIENT_ID on the server)"
            )
            raise ValueError(msg) from exc
        if isinstance(exc, httpx.TimeoutException):
            msg = (
                f"stepik import timed out for course {course_id}: "
                "course is too large or Stepik is slow — try again"
            )
            raise ValueError(msg) from exc
        msg = f"stepik import failed for course {course_id}: {detail}"
        raise ValueError(msg) from exc


def _import_fixture(course_id: str) -> tuple[dict[str, object], dict[str, object]]:
    payload = _load_fixture(course_id)
    steps = _fixture_steps(payload)
    pack = {
        "platform": "stepik",
        "external_id": course_id,
        "title": payload["title"],
        "slug": f"stepik-{course_id}",
        "version": payload.get("version", "1.0.0"),
        "locale": payload.get("locale", "en"),
        "topics": payload["topics"],
        "steps": steps,
        "course_assess": payload.get("course_assess", []),
    }
    report = {
        "total_items": len(steps),
        "imported_full": sum(
            1 for step in steps.values() if step.get("fidelity", "full") == "full"
        ),
        "imported_partial": sum(
            1 for step in steps.values() if step.get("fidelity") == "partial"
        ),
        "skipped": 0,
        "warnings": [],
    }
    return pack, report


def _import_live(
    course_id: str,
    *,
    token: str | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
        course_payload = _api_get(client, f"courses/{course_id}", token=token)
        courses = course_payload.get("courses")
        if not isinstance(courses, list) or not courses:
            msg = f"stepik course {course_id} not found"
            raise ValueError(msg)
        course = courses[0]
        if not isinstance(course, dict):
            msg = "invalid course payload"
            raise ValueError(msg)

        title = str(course.get("title") or f"Stepik {course_id}")
        section_ids = [str(item) for item in course.get("sections") or [] if item is not None]
        sections_by_id = _fetch_resources(client, "sections", section_ids, token=token)

        unit_ids: list[str] = []
        for section_id in section_ids:
            section = sections_by_id.get(section_id)
            if not section:
                continue
            unit_ids.extend(str(uid) for uid in section.get("units") or [] if uid is not None)
        units_by_id = _fetch_resources(client, "units", unit_ids, token=token)

        lesson_ids: list[str] = []
        for unit_id in unit_ids:
            unit = units_by_id.get(unit_id)
            if not unit:
                continue
            lesson_id = unit.get("lesson")
            if lesson_id is not None:
                lesson_ids.append(str(lesson_id))
        lessons_by_id = _fetch_resources(client, "lessons", lesson_ids, token=token)

        step_ids: list[str] = []
        for lesson_id in lesson_ids:
            lesson = lessons_by_id.get(lesson_id)
            if not lesson:
                continue
            step_ids.extend(str(sid) for sid in lesson.get("steps") or [] if sid is not None)

        truncated = len(step_ids) > _MAX_STEPS
        limited_step_ids = step_ids[:_MAX_STEPS]
        sources = _fetch_step_sources(client, limited_step_ids, token=token)
        sources_by_id = {str(item.get("id")): item for item in sources if item.get("id") is not None}

        topics: list[dict[str, object]] = []
        steps: dict[str, dict[str, object]] = {}
        full = 0
        partial = 0
        warnings: list[dict[str, str]] = []
        imported_step_ids: set[str] = set()

        for section_id in section_ids:
            section = sections_by_id.get(section_id) or {}
            topic_id = f"section-{section_id}"
            study_ids: list[str] = []
            practice_ids: list[str] = []

            for unit_id in [str(uid) for uid in section.get("units") or [] if uid is not None]:
                unit = units_by_id.get(unit_id) or {}
                lesson_id = unit.get("lesson")
                if lesson_id is None:
                    continue
                lesson = lessons_by_id.get(str(lesson_id)) or {}
                for raw_sid in lesson.get("steps") or []:
                    sid = str(raw_sid)
                    if sid not in sources_by_id or sid in imported_step_ids:
                        continue
                    mapped_id = f"step-{sid}"
                    phase_guess = _phase_for_source(sources_by_id[sid])
                    built, fidelity, warning = _map_step_source(
                        sources_by_id[sid],
                        step_id=mapped_id,
                        phase=phase_guess,
                        fallback_title=str(lesson.get("title") or ""),
                    )
                    steps[mapped_id] = built
                    imported_step_ids.add(sid)
                    if fidelity == "full":
                        full += 1
                    else:
                        partial += 1
                                                                                         
                    if phase_guess == "study":
                        study_ids.append(mapped_id)
                    else:
                        practice_ids.append(mapped_id)
                    if warning:
                        warnings.append({"step": mapped_id, "reason": warning})

            if study_ids or practice_ids:
                topics.append(
                    {
                        "id": topic_id,
                        "title": str(section.get("title") or topic_id),
                        "study": study_ids,
                        "practice": practice_ids,
                        "assess": [],
                    }
                )

        if truncated:
            warnings.append(
                {
                    "step": "course",
                    "reason": f"imported first {_MAX_STEPS} of {len(step_ids)} steps",
                }
            )

        if not topics or not steps:
            msg = f"stepik course {course_id} has no importable steps"
            raise ValueError(msg)

        pack = {
            "platform": "stepik",
            "external_id": course_id,
            "title": title,
            "slug": f"stepik-{course_id}",
            "version": "1.0.0",
            "locale": "ru",
            "topics": topics,
            "steps": steps,
            "course_assess": [],
        }
        report = {
            "total_items": len(steps),
            "imported_full": full,
            "imported_partial": partial,
            "skipped": max(0, len(step_ids) - len(steps)),
            "warnings": warnings,
        }
        return pack, report


def _fetch_resources(
    client: httpx.Client,
    resource: str,
    ids: list[str],
    *,
    token: str | None = None,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    unique_ids = list(dict.fromkeys(ids))
    for offset in range(0, len(unique_ids), _BATCH_SIZE):
        chunk = unique_ids[offset : offset + _BATCH_SIZE]
        if not chunk:
            continue
        params = [("ids[]", item) for item in chunk]
        payload = _api_get(client, resource, token=token, params=params)
        rows = payload.get(resource) or []
        for row in rows:
            if isinstance(row, dict) and row.get("id") is not None:
                result[str(row["id"])] = row
    return result


def _fetch_step_sources(
    client: httpx.Client,
    step_ids: list[str],
    *,
    token: str | None = None,
) -> list[dict[str, Any]]:
                                                                                         
    if not step_ids:
        return []

    by_id: dict[str, dict[str, Any]] = {}
    for offset in range(0, len(step_ids), _BATCH_SIZE):
        chunk = step_ids[offset : offset + _BATCH_SIZE]
        params = [("ids[]", step_id) for step_id in chunk]
        payload = _api_get(client, "steps", token=token, params=params)
        for item in payload.get("steps") or []:
            if isinstance(item, dict) and item.get("id") is not None:
                by_id[str(item["id"])] = item

                                                                                        
    for sid, step in list(by_id.items()):
        if not _looks_truncated(_block_text(step)):
            continue
        try:
            payload = _api_get(client, f"steps/{sid}", token=token)
        except httpx.HTTPError:
            continue
        rows = payload.get("steps") or []
        if not rows or not isinstance(rows[0], dict):
            continue
        if len(_block_text(rows[0])) > len(_block_text(step)):
            by_id[sid] = rows[0]

                                                               
    if token:
        for offset in range(0, len(step_ids), _BATCH_SIZE):
            chunk = step_ids[offset : offset + _BATCH_SIZE]
            params = [("ids[]", step_id) for step_id in chunk]
            try:
                payload = _api_get(client, "step-sources", token=token, params=params)
            except httpx.HTTPError:
                continue
            for item in payload.get("step-sources") or []:
                if not isinstance(item, dict) or item.get("id") is None:
                    continue
                sid = str(item["id"])
                current = by_id.get(sid)
                by_id[sid] = _merge_step_payload(current, item) if current else item

                                                                                    
    _hydrate_choice_datasets(client, by_id, token=token)

    return [by_id[sid] for sid in step_ids if sid in by_id]


def _block_text(source: dict[str, Any]) -> str:
    block = source.get("block")
    if not isinstance(block, dict):
        return ""
    return str(block.get("text") or "")


def _looks_truncated(text: str) -> bool:
    if not text:
        return False
    length = len(text)
    if length == 400:
        return True
    if 380 <= length <= 420:
        stripped = text.rstrip()
        if not stripped.endswith((".", "!", "?", "…", ">", '"', "'", "»")):
            return True
    if "<" in text and text.count("<") > text.count(">"):
        return True
    return False


def _step_title(
    source: dict[str, Any],
    *,
    block_name: str,
    fallback_title: str,
    step_id: str,
) -> str:
    raw = str(source.get("title") or "").strip()
    weak = {"", block_name, "text", "video", "code", "choice", "quiz", "string", "number"}
    if raw.casefold() not in {item.casefold() for item in weak}:
        return raw
    lesson_title = fallback_title.strip()
    if lesson_title:
        return lesson_title
    heading = re.search(
        r"(?is)<h[1-3][^>]*>(.*?)</h[1-3]>",
        str((source.get("block") or {}).get("text") or ""),
    )
    if heading:
        cleaned = _plain_text(heading.group(1), limit=120)
        if cleaned:
            return cleaned
    return raw or block_name or step_id


def _map_step_source(
    source: dict[str, Any],
    *,
    step_id: str,
    phase: str,
    fallback_title: str = "",
) -> tuple[dict[str, object], str, str | None]:
    block = source.get("block")
    block_dict = block if isinstance(block, dict) else {}
    block_name = str(block_dict.get("name") or "text").strip().casefold()
    title = _step_title(source, block_name=block_name, fallback_title=fallback_title, step_id=step_id)
    raw_html = str(block_dict.get("text") or "")
    text = _plain_text(raw_html, limit=_STEP_TEXT_LIMIT) or title
    study = _study_fields(raw_html, fallback_text=text)
    safe_phase = phase if phase in {"study", "practice", "assess"} else "study"

    if block_name == "text":
                                                                              
                                                                    
        if _text_looks_like_code_task(text, raw_html, title=title):
            runtime, runtime_version, template = _extract_code_template(block_dict)
            if runtime == "python" and not template and _sqlish_text(f"{title}\n{text}\n{raw_html}"):
                runtime, runtime_version = "sql", "15"
            return (
                {
                    "id": step_id,
                    "kind": "code",
                    "title": title,
                    "phase": "practice" if safe_phase == "study" else safe_phase,
                    "fidelity": "partial",
                    "payload": {
                        **study,
                        "runtime": runtime,
                        "runtime_version": runtime_version,
                        "template": template,
                        "tests": [],
                        "stepik_language": _stepik_language_hint(block_dict, runtime),
                    },
                },
                "partial",
                "text block recovered as code task from assignment cues",
            )
        return (
            {
                "id": step_id,
                "kind": "theory",
                "title": title,
                "phase": safe_phase,
                "fidelity": "full",
                "payload": study,
            },
            "full",
            None,
        )

    if block_name == "video":
        video_url, poster_url = _extract_video_meta(block_dict)
        payload: dict[str, object] = dict(study)
        if video_url:
            payload["video_url"] = video_url
        if poster_url:
            payload["poster_url"] = poster_url
        fidelity = "full" if video_url else "partial"
        warning = None if video_url else "video URL was not available from Stepik"
        return (
            {
                "id": step_id,
                "kind": "video",
                "title": title,
                "phase": safe_phase,
                "fidelity": fidelity,
                "payload": payload,
            },
            fidelity,
            warning,
        )

    if block_name in {"code", "sql", "linux-code"}:
        runtime, runtime_version, template = _extract_code_template(block_dict)
        if block_name == "sql" or (runtime == "python" and not template and _sqlish_text(f"{title}\n{text}")):
            runtime, runtime_version = "sql", "15"
        return (
            {
                "id": step_id,
                "kind": "code",
                "title": title,
                "phase": safe_phase,
                "fidelity": "partial",
                "payload": {
                    **study,
                    "runtime": runtime,
                    "runtime_version": runtime_version,
                    "template": template,
                    "tests": [],
                    "stepik_language": _stepik_language_hint(block_dict, runtime),
                    "stepik_reply": "solve_sql" if runtime == "sql" or block_name == "sql" else "code",
                },
            },
            "partial",
            "code tests are not imported from Stepik",
        )

    if block_name == "choice":
        choices, answer = _extract_choice_quiz(block_dict)
        payload = {**study, "question": text, "choices": choices}
        if answer is not None:
            payload["answer"] = answer
        if choices and answer is not None:
            fidelity = "full"
            warning = None
        elif choices:
            fidelity = "partial"
            warning = "choice answer key is not available without Stepik author access"
        else:
            fidelity = "partial"
            warning = "choice quiz options were not available from Stepik"
        return (
            {
                "id": step_id,
                "kind": "quiz",
                "title": title,
                "phase": safe_phase,
                "fidelity": fidelity,
                "payload": payload,
            },
            fidelity,
            warning,
        )

    if block_name in {"matching", "sorting", "table", "string", "number", "math", "free-answer", "dataset"}:
                                                                                                
        if block_name in {"string", "free-answer", "dataset"} and _sqlish_text(f"{title}\n{text}\n{raw_html}"):
            return (
                {
                    "id": step_id,
                    "kind": "code",
                    "title": title,
                    "phase": safe_phase,
                    "fidelity": "partial",
                    "payload": {
                        **study,
                        "runtime": "sql",
                        "runtime_version": "15",
                        "template": "",
                        "tests": [],
                        "stepik_language": "sql",
                        "stepik_reply": "solve_sql",
                    },
                },
                "partial",
                f"{block_name} recovered as SQL code task",
            )
        return (
            {
                "id": step_id,
                "kind": "quiz",
                "title": title,
                "phase": safe_phase,
                "fidelity": "partial",
                "payload": {
                    **study,
                    "question": text,
                    "choices": [],
                },
            },
            "partial",
            f"{block_name} quiz options are not fully imported",
        )

                                                                                           
    if _text_looks_like_code_task(text, raw_html, title=title):
        runtime, runtime_version = ("sql", "15") if _sqlish_text(f"{title}\n{text}") else ("python", "3.12")
        return (
            {
                "id": step_id,
                "kind": "code",
                "title": title,
                "phase": safe_phase if safe_phase != "study" else "practice",
                "fidelity": "partial",
                "payload": {
                    **study,
                    "runtime": runtime,
                    "runtime_version": runtime_version,
                    "template": "",
                    "tests": [],
                    "stepik_language": _stepik_language_hint(block_dict, runtime),
                },
            },
            "partial",
            f"unsupported block type {block_name} recovered as code task",
        )

    return (
        {
            "id": step_id,
            "kind": "theory",
            "title": title,
            "phase": safe_phase,
            "fidelity": "partial",
            "payload": {
                **study,
                "instructions": text or f"Unsupported Stepik block: {block_name}",
            },
        },
        "partial",
        f"unsupported block type {block_name}",
    )


def _study_fields(raw_html: str, *, fallback_text: str) -> dict[str, object]:
    body_html, images, examples = _prepare_study_html(raw_html)
    if not body_html:
                                                                                                    
        plain_source = _plain_text_preserve_columns(raw_html, limit=_STEP_TEXT_LIMIT) or fallback_text
        if plain_source.strip():
            body_html = _plain_text_as_html(plain_source)
    payload: dict[str, object] = {
        "instructions": fallback_text,
    }
    if body_html:
        payload["body_html"] = body_html
    if images:
        payload["images"] = images
    if examples:
        payload["code_examples"] = examples
    return payload


def _plain_text_as_html(text: str) -> str:
                                                                                           
                                                                                   
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return ""
    as_table = _ascii_table_to_html(cleaned)
    if as_table:
        return as_table

    chunks = [part.strip() for part in re.split(r"\n\s*\n+", cleaned) if part.strip()]
    parts: list[str] = []
    for chunk in chunks:
        table = _ascii_table_to_html(chunk)
        if table:
            parts.append(table)
            continue
        lines = [line.rstrip() for line in chunk.split("\n") if line.strip()]
        tabular = [line for line in lines if "\t" in line or re.search(r"\s{2,}", line)]
        if len(lines) >= 2 and len(tabular) == len(lines):
            table = _ascii_table_to_html("\n".join(lines))
            if table:
                parts.append(table)
                continue
        body = chunk
        if len(body) > 220 and "\n" not in body:
            sentences = re.split(r"(?<=[.!?…])\s+", body)
            grouped: list[str] = []
            buf: list[str] = []
            for sentence in sentences:
                if not sentence.strip():
                    continue
                buf.append(sentence.strip())
                if len(buf) >= 2 or sum(len(item) for item in buf) >= 220:
                    grouped.append(" ".join(buf))
                    buf = []
            if buf:
                grouped.append(" ".join(buf))
            for paragraph in grouped or [body]:
                parts.append(f"<p>{html.escape(paragraph)}</p>")
            continue
        if "\n" in body and not tabular:
            for line in lines:
                parts.append(f"<p>{html.escape(line.strip())}</p>")
            continue
        parts.append(f"<p>{html.escape(re.sub(r'[ \t]{2,}', ' ', body).strip())}</p>")
    return "".join(parts)


def _ascii_table_to_html(block: str) -> str:
    lines = [line.rstrip() for line in block.split("\n") if line.strip()]
    if len(lines) < 2:
        return ""

    def split_row(line: str) -> list[str]:
        if "\t" in line:
            return [cell.strip() for cell in line.split("\t") if cell.strip()]
        if re.search(r"\s{2,}", line):
            return [cell.strip() for cell in re.split(r"\s{2,}", line) if cell.strip()]
        return []

    rows = [split_row(line) for line in lines]
    if any(len(row) < 2 for row in rows):
        return ""
    width = len(rows[0])
    if width < 2 or any(len(row) != width for row in rows):
        return ""
    header, *body = rows
    th = "".join(f"<th>{html.escape(cell)}</th>" for cell in header)
    tr = "".join(
        "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>" for row in body
    )
    return f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def _prepare_study_html(raw_html: str) -> tuple[str, list[str], list[dict[str, str]]]:
    if not raw_html or not raw_html.strip():
        return "", [], []
    sanitizer = _StudyHtmlSanitizer(base_url=_STEPIK_ORIGIN)
    try:
        sanitizer.feed(raw_html)
        sanitizer.close()
    except Exception:
        return "", [], []
    body = sanitizer.result()[:_HTML_LIMIT]
    return body, sanitizer.images, sanitizer.code_examples


class _StudyHtmlSanitizer(HTMLParser):
    def __init__(self, *, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url.rstrip("/") + "/"
        self._parts: list[str] = []
        self._skip_depth = 0
        self._pre_depth = 0
        self._code_stack: list[list[str]] = []
        self.images: list[str] = []
        self.code_examples: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "iframe", "object", "embed", "form", "input", "button"}:
            self._skip_depth += 1
            return
        if self._skip_depth or lower not in _ALLOWED_TAGS:
            return
        attr_map = {key.lower(): (value or "") for key, value in attrs if key}
        kept: list[str] = []
        if lower == "a":
            href = self._absolutize(attr_map.get("href", ""))
            if href.startswith(("http://", "https://")):
                kept.append(f'href="{html.escape(href, quote=True)}"')
                kept.append('rel="noopener noreferrer"')
                kept.append('target="_blank"')
        elif lower == "img":
            src = self._absolutize(attr_map.get("src", ""))
            if not src.startswith(("http://", "https://")):
                return
            kept.append(f'src="{html.escape(src, quote=True)}"')
            alt = attr_map.get("alt", "")
            if alt:
                kept.append(f'alt="{html.escape(alt, quote=True)}"')
            kept.append('loading="lazy"')
            if src not in self.images:
                self.images.append(src)
        elif lower == "pre":
            self._pre_depth += 1
        elif lower == "code":
            klass = attr_map.get("class", "")
            if klass:
                kept.append(f'class="{html.escape(klass, quote=True)}"')
            if self._pre_depth:
                self._code_stack.append([])
        attr_html = ((" " + " ".join(kept)) if kept else "")
        if lower in _VOID_TAGS:
            self._parts.append(f"<{lower}{attr_html} />")
            return
        self._parts.append(f"<{lower}{attr_html}>")

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower in {"script", "style", "iframe", "object", "embed", "form", "input", "button"}:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth or lower not in _ALLOWED_TAGS or lower in _VOID_TAGS:
            return
        if lower == "code" and self._code_stack:
            code = "".join(self._code_stack.pop()).strip("\n")
            if code.strip() and len(code) <= 12_000:
                self.code_examples.append({"language": "", "code": code})
        if lower == "pre" and self._pre_depth:
            self._pre_depth -= 1
        self._parts.append(f"</{lower}>")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        escaped = html.escape(data, quote=False)
        self._parts.append(escaped)
        if self._code_stack:
            self._code_stack[-1].append(data)

    def handle_entityref(self, name: str) -> None:
        self.handle_data(html.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self.handle_data(html.unescape(f"&#{name};"))

    def result(self) -> str:
        text = "".join(self._parts).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text

    def _absolutize(self, url: str) -> str:
        value = html.unescape(url.strip())
        if not value or value.startswith(("#", "javascript:", "data:")):
            return ""
        if value.startswith("//"):
            return "https:" + value
        return urljoin(self._base_url, value)


def _extract_video_meta(block: dict[str, Any]) -> tuple[str | None, str | None]:
    return _extract_video_url(block), _extract_video_poster(block)


def _extract_video_url(block: dict[str, Any]) -> str | None:
    video = block.get("video")
    if isinstance(video, str) and video.startswith(("http://", "https://")):
        return video
    if isinstance(video, dict):
        candidates: list[tuple[int, str]] = []
        urls = video.get("urls")
        if isinstance(urls, list):
            for item in urls:
                if not isinstance(item, dict):
                    continue
                url = item.get("url")
                if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                    continue
                quality_raw = item.get("quality")
                try:
                    quality = int(str(quality_raw).removesuffix("p"))
                except ValueError:
                    quality = 0
                candidates.append((quality, url))
        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            return candidates[0][1]

        for key in ("url", "external", "upload"):
            value = video.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value

    for key in ("video_url", "url"):
        value = block.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value

    return _video_url_from_text(str(block.get("text") or ""))


def _extract_video_poster(block: dict[str, Any]) -> str | None:
    video = block.get("video")
    if not isinstance(video, dict):
        return None
    for key in ("thumbnail", "cover", "poster", "preview", "image"):
        value = video.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
        if isinstance(value, dict):
            for nested_key in ("url", "src", "hd", "sd"):
                nested = value.get(nested_key)
                if isinstance(nested, str) and nested.startswith(("http://", "https://")):
                    return nested
    urls = video.get("urls")
    if isinstance(urls, list):
        for item in urls:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            if isinstance(url, str) and url.startswith(("http://", "https://")) and re.search(
                r"\.(jpe?g|png|webp)(?:$|\?)",
                url,
                flags=re.IGNORECASE,
            ):
                return url
    return None


def _video_url_from_text(text: str) -> str | None:
    yt = re.search(
        r"(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([\w-]{6,})",
        text,
        flags=re.IGNORECASE,
    )
    if yt:
        return f"https://www.youtube.com/watch?v={yt.group(1)}"
    mp4 = re.search(r"https?://[^\s\"'<>]+\.mp4(?:\?[^\s\"'<>]*)?", text, flags=re.IGNORECASE)
    if mp4:
        return mp4.group(0)
    return None


def _extract_code_template(block: dict[str, Any]) -> tuple[str, str, str]:
    source = block.get("source")
    container = source if isinstance(source, dict) else {}
    templates = _coerce_templates(container.get("templates_data"))
    if not templates:
        templates = _coerce_templates(container.get("code_templates"))
    if not templates:
        templates = _coerce_templates(block.get("templates_data"))

    preferred_keys = (
        "python3",
        "python",
        "py",
        "javascript",
        "js",
        "java",
        "cpp",
        "c++",
        "c",
        "go",
        "sql",
    )
    if templates:
        for key in preferred_keys:
            if key in templates and templates[key].strip():
                runtime, version = _runtime_from_lang(key)
                return runtime, version, templates[key]
        first_key, first_code = next(iter(templates.items()))
        if first_code.strip():
            runtime, version = _runtime_from_lang(first_key)
            return runtime, version, first_code

    for key in ("code", "template", "solution_template"):
        value = container.get(key)
        if isinstance(value, str) and value.strip():
            return "python", "3.12", value
        if isinstance(value, dict):
            nested = _coerce_templates(value)
            if nested:
                lang, code = next(iter(nested.items()))
                runtime, version = _runtime_from_lang(lang)
                return runtime, version, code

    languages = container.get("languages")
    if isinstance(languages, list) and languages:
        first = str(languages[0])
        runtime, version = _runtime_from_lang(first)
        return runtime, version, ""
    return "python", "3.12", ""


def _coerce_templates(value: object) -> dict[str, str]:
    raw: object = value
    if isinstance(raw, str) and raw.strip():
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {"python3": raw}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key, item in raw.items():
        if isinstance(item, str) and item.strip():
            out[str(key).casefold()] = item
        elif isinstance(item, dict):
            nested = item.get("template") or item.get("code") or item.get("text")
            if isinstance(nested, str) and nested.strip():
                out[str(key).casefold()] = nested
    return out


def _runtime_from_lang(language: str) -> tuple[str, str]:
    key = language.casefold().replace(" ", "")
    for alias, mapped in _RUNTIME_ALIASES.items():
        if alias in key or key.startswith(alias):
            return mapped
    return "python", "3.12"


def _merge_step_payload(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
                                                                                      
    merged = dict(base)
    for key, value in overlay.items():
        if key == "block" and isinstance(value, dict):
            current_block = merged.get("block")
            merged["block"] = (
                _merge_step_block(current_block, value)
                if isinstance(current_block, dict)
                else value
            )
            continue
        if value is None:
            continue
        if key == "title" and not str(value).strip() and merged.get("title"):
            continue
        merged[key] = value
    return merged


def _merge_step_block(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    out.update({key: value for key, value in overlay.items() if value is not None})
    base_text = str(base.get("text") or "")
    overlay_text = str(overlay.get("text") or "")
    if len(base_text) > len(overlay_text):
        out["text"] = base.get("text")
    for key in ("source", "dataset", "options"):
        base_value = base.get(key)
        overlay_value = overlay.get(key)
        if isinstance(overlay_value, dict) and overlay_value:
            if isinstance(base_value, dict):
                combined = dict(base_value)
                combined.update(overlay_value)
                base_options = base_value.get("options")
                overlay_options = overlay_value.get("options")
                if isinstance(overlay_options, list) and overlay_options:
                    combined["options"] = overlay_options
                elif isinstance(base_options, list) and base_options:
                    combined["options"] = base_options
                out[key] = combined
            else:
                out[key] = overlay_value
        elif overlay_value not in (None, {}, []) and base_value in (None, {}, []):
            out[key] = overlay_value
        elif key not in overlay and base_value not in (None, {}, []):
            out[key] = base_value
    return out


def _hydrate_choice_datasets(
    client: httpx.Client,
    steps_by_id: dict[str, dict[str, Any]],
    *,
    token: str | None = None,
) -> None:
                                                                                   
    pending = [
        sid
        for sid, step in steps_by_id.items()
        if isinstance(step.get("block"), dict)
        and str(step["block"].get("name") or "").casefold() == "choice"
        and not _extract_choice_quiz(step["block"])[0]
    ]
    if not pending:
        return
    _ensure_stepik_csrf(client)
    for sid in pending:
        dataset = _fetch_attempt_dataset(client, sid, token=token)
        if not dataset:
            continue
        step = steps_by_id[sid]
        block = dict(step["block"])
        block["dataset"] = dataset
        steps_by_id[sid] = {**step, "block": block}


def _ensure_stepik_csrf(client: httpx.Client) -> None:
    if client.cookies.get("csrftoken"):
        return
    try:
        client.get(_STEPIK_ORIGIN + "/", headers={"Accept": "text/html"})
    except httpx.HTTPError:
        return


def _fetch_attempt_dataset(
    client: httpx.Client,
    step_id: str,
    *,
    token: str | None = None,
) -> dict[str, Any] | None:
    csrf = client.cookies.get("csrftoken")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": _STEPIK_ORIGIN + "/",
        "Origin": _STEPIK_ORIGIN,
    }
    if csrf:
        headers["X-CSRFToken"] = csrf
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = client.post(
            f"{_API}/attempts",
            headers=headers,
            json={"attempt": {"step": int(step_id) if step_id.isdigit() else step_id}},
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    rows = payload.get("attempts") or []
    if not rows or not isinstance(rows[0], dict):
        return None
    dataset = rows[0].get("dataset")
    if not isinstance(dataset, dict):
        return None
    options = dataset.get("options")
    if not isinstance(options, list) or not options:
        return None
    return dataset


def _extract_choice_quiz(block: dict[str, Any]) -> tuple[list[str], int | None]:
                                                                                       
    option_rows: list[dict[str, Any]] = []
    string_rows: list[str] = []

    containers: list[Any] = [block.get("source"), block.get("dataset"), block.get("options")]
    for container in containers:
        if isinstance(container, list):
            for option in container:
                if isinstance(option, dict):
                    option_rows.append(option)
                elif isinstance(option, str) and option.strip():
                    string_rows.append(option.strip())
            continue
        if not isinstance(container, dict):
            continue
        options = container.get("options")
        if not isinstance(options, list):
            continue
        for option in options:
            if isinstance(option, dict):
                option_rows.append(option)
            elif isinstance(option, str) and option.strip():
                string_rows.append(option.strip())

    choices: list[str] = []
    answer: int | None = None
    if option_rows:
        for option in option_rows:
            label = option.get("text")
            if label is None:
                label = option.get("name")
            text = _plain_text(str(label or ""), limit=2_000)
            if not text:
                continue
            if option.get("is_correct") is True and answer is None:
                answer = len(choices)
            choices.append(text)
        return choices, answer

    cleaned_strings = [_plain_text(item, limit=2_000) for item in string_rows]
    return [item for item in cleaned_strings if item], None


def _phase_for_source(source: dict[str, Any]) -> str:
    block = source.get("block")
    block_dict = block if isinstance(block, dict) else {}
    block_name = str(block_dict.get("name") or "text").strip().casefold()
    if block_name in {"text", "video"}:
        raw_html = str(block_dict.get("text") or "")
        title = str(source.get("title") or "")
        text = _plain_text(raw_html, limit=4_000) or title
        if block_name == "text" and _text_looks_like_code_task(text, raw_html, title=title):
            return "practice"
        return "study"
    return "practice"


def _text_looks_like_code_task(text: str, raw_html: str, *, title: str = "") -> bool:
    blob = f"{title}\n{text}\n{raw_html}"
    lowered = blob.casefold()
    if re.search(r"задач[аеи]\s*\d+", lowered) or "задани" in lowered:
        return bool(_sqlish_text(blob) or re.search(r"\b(def |class |function |print\()", lowered))
    if not (
        re.search(r"задани[ея]\s*:", lowered)
        or re.search(r"напишите\s+(запрос|код|функц|программ)", lowered)
    ):
        return False
    return bool(
        _sqlish_text(blob)
        or re.search(r"\b(def |class |function |print\(|return )", lowered)
    )


def _sqlish_text(blob: str) -> bool:
    return bool(
        re.search(
            r"\b(select|insert|update|delete|create\s+table|join|group\s+by|"
            r"order\s+by|where|limit|offset|distinct|\bsql\b)\b",
            blob,
            flags=re.IGNORECASE,
        )
    )


def _stepik_language_hint(block: dict[str, Any], runtime: str) -> str:
    source = block.get("source")
    container = source if isinstance(source, dict) else {}
    languages = container.get("languages")
    if isinstance(languages, list) and languages:
        first = str(languages[0]).strip()
        if first:
            return first
    templates = _coerce_templates(container.get("templates_data")) or _coerce_templates(
        container.get("code_templates")
    )
    if templates:
        return next(iter(templates.keys()))
    mapping = {
        "python": "python3",
        "javascript": "javascript",
        "typescript": "javascript",
        "sql": "sql",
        "java": "java",
        "cpp": "c++",
        "c": "c",
        "go": "go",
        "rust": "rust",
    }
    return mapping.get(runtime, runtime)


def _maybe_access_token(
    *,
    username: str = "",
    password: str = "",
    client_id: str = "",
    client_secret: str = "",
    **_ignored: object,
) -> str | None:
    user = username.strip()
    secret = password.strip()
    if not user or not secret:
        return None
    oauth_id = client_id.strip() or os.getenv("STEPIK_CLIENT_ID", "").strip()
    oauth_secret = client_secret.strip() or os.getenv("STEPIK_CLIENT_SECRET", "").strip()
    if not oauth_id:
        raise ValueError(
            "stepik Client ID required "
            "(set STEPIK_CLIENT_ID on the server or save Client ID in settings; "
            "create a Confidential app at https://stepik.org/oauth2/applications/)"
        )
    if not oauth_secret:
        raise ValueError(
            "stepik Client secret required "
            "(create a Confidential app at https://stepik.org/oauth2/applications/ "
            "with grant type Resource owner password-based)"
        )
    data = {
        "grant_type": "password",
        "username": user,
        "password": secret,
    }
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT) as client:
            response = client.post(_TOKEN_URL, data=data, auth=(oauth_id, oauth_secret))
            if response.status_code >= 400:
                detail = _token_error_detail(response)
                raise ValueError(detail)
            payload = response.json()
    except httpx.HTTPError as exc:
        raise ValueError(f"stepik token request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("stepik token response is invalid")
    token = payload.get("access_token")
    if isinstance(token, str) and token:
        return token
    raise ValueError("stepik token response has no access_token")


def _token_error_detail(response: httpx.Response) -> str:
    body: object
    try:
        body = response.json()
    except ValueError:
        body = None
    oauth_error = ""
    if isinstance(body, dict):
        oauth_error = str(body.get("error") or body.get("error_description") or "").strip()
    if oauth_error == "unauthorized_client":
        return (
            "stepik rejected the OAuth app (unauthorized_client). "
            "Recreate the application at https://stepik.org/oauth2/applications/: "
            "Client type = Confidential, "
            "Authorization grant type = Resource owner password-based, "
            "then paste the new Client ID and Client secret into Settings"
        )
    if oauth_error == "invalid_client":
        return (
            "stepik Client ID or Client secret is invalid — "
            "copy both again from https://stepik.org/oauth2/applications/"
        )
    if oauth_error in {"invalid_grant", "invalid_credentials"}:
        return "stepik email or password is wrong"
    if oauth_error:
        return f"stepik OAuth error: {oauth_error} (HTTP {response.status_code})"
    text = response.text.strip()[:200]
    return f"stepik OAuth failed HTTP {response.status_code}: {text or 'no details'}"


def _api_get(
    client: httpx.Client,
    path: str,
    *,
    token: str | None = None,
    params: dict[str, str] | list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = client.get(f"{_API}/{path}", headers=headers, params=params)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        msg = f"unexpected stepik response for {path}"
        raise ValueError(msg)
    return payload


def _courses_to_catalog(courses: object) -> list[dict[str, object]]:
    if not isinstance(courses, list):
        return []
    items: list[dict[str, object]] = []
    for course in courses:
        if not isinstance(course, dict):
            continue
        course_id = course.get("id")
        title = course.get("title")
        if course_id is None or not isinstance(title, str) or not title.strip():
            continue
        summary = course.get("summary") or course.get("description") or ""
        author = _course_author(course)
        language = _course_language(course)
        tags = _infer_tags(title, str(summary), language)
        items.append(
            {
                "id": str(course_id),
                "external_id": str(course_id),
                "platform": "stepik",
                "title": title.strip(),
                "description": _plain_text(str(summary), limit=_CATALOG_TEXT_LIMIT),
                "author": author,
                "language": language,
                "tags": tags,
            }
        )
    return items


def _course_author(course: dict[str, Any]) -> str:
    authors = course.get("authors") or course.get("instructors") or []
    if isinstance(authors, list) and authors:
        first = authors[0]
        if isinstance(first, dict):
            for key in ("full_name", "name", "username"):
                value = first.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        if isinstance(first, str) and first.strip():
            return first.strip()
    owner = course.get("owner")
    if isinstance(owner, dict):
        for key in ("full_name", "name", "username"):
            value = owner.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def _course_language(course: dict[str, Any]) -> str:
    for key in ("language", "default_language"):
        value = course.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return ""


def _infer_tags(title: str, description: str, language: str) -> list[str]:
    hay = f" {title} {description} ".casefold()
    tags: list[str] = []
    for label, needles in _TOPIC_HINTS:
        if any(needle in hay for needle in needles):
            tags.append(label)
                                                                       
    return tags[:6]


def _plain_text_preserve_columns(value: str, *, limit: int | None = None) -> str:
    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", value)
    cleaned = re.sub(r"(?i)</p\s*>", "\n\n", cleaned)
    cleaned = re.sub(r"(?i)</li\s*>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</h[1-6]\s*>", "\n\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if limit is None:
        return cleaned
    return cleaned[:limit]


def _plain_text(value: str, *, limit: int | None = None) -> str:
    cleaned = _plain_text_preserve_columns(value, limit=None)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    if limit is None:
        return cleaned
    return cleaned[:limit]


def _fixture_exists(course_id: str) -> bool:
    return (_FIXTURES / f"course_{course_id}.json").is_file()


def _fixture_steps(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    steps_raw = payload.get("steps")
    if not isinstance(steps_raw, dict):
        msg = "fixture missing steps"
        raise ValueError(msg)
    return {
        key: value
        for key, value in steps_raw.items()
        if isinstance(key, str) and isinstance(value, dict)
    }


def _load_fixture(course_id: str) -> dict[str, object]:
    path = _FIXTURES / f"course_{course_id}.json"
    if not path.is_file():
        msg = f"stepik course {course_id} not found in fixtures"
        raise ValueError(msg)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "fixture must be a JSON object"
        raise ValueError(msg)
    return payload
