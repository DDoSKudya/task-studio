from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

CourseBuildStatus = Literal["running", "paused", "failed", "done"]

_META = "meta.json"
_REQUEST = "request.json"
_ANALYZE = "artifacts/analyze.json"
_COMPILER = "artifacts/compiler.json"
_BLUEPRINT = "artifacts/blueprint.json"
_TOPICS = "artifacts/topics"
_THEORY = "artifacts/theory"
_SECTIONS = "artifacts/sections"
_QUIZZES = "artifacts/quizzes.json"
_CODE = "artifacts/code.json"
_TTL_DEFAULT_DAYS = 30


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class CourseBuildMeta:
    build_id: str
    user_id: str
    status: CourseBuildStatus
    stage: str
    title: str
    progress: float
    message: str
    chapter_total: int
    chapters_done: int
    error: str | None
    created_at: str
    updated_at: str
    mode: str

    def to_dict(self) -> dict[str, object]:
        return {
            "build_id": self.build_id,
            "user_id": self.user_id,
            "status": self.status,
            "stage": self.stage,
            "title": self.title,
            "progress": self.progress,
            "message": self.message,
            "chapter_total": self.chapter_total,
            "chapters_done": self.chapters_done,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CourseBuildMeta:
        status_raw = str(raw.get("status") or "paused")
        status: CourseBuildStatus
        if status_raw == "running":
            status = "running"
        elif status_raw == "failed":
            status = "failed"
        elif status_raw == "done":
            status = "done"
        else:
            status = "paused"
        return cls(
            build_id=str(raw["build_id"]),
            user_id=str(raw["user_id"]),
            status=status,
            stage=str(raw.get("stage") or "analyze"),
            title=str(raw.get("title") or "Course draft"),
            progress=float(raw.get("progress") or 0.0),
            message=str(raw.get("message") or ""),
            chapter_total=int(raw.get("chapter_total") or 0),
            chapters_done=int(raw.get("chapters_done") or 0),
            error=str(raw["error"]) if raw.get("error") else None,
            created_at=str(raw.get("created_at") or _iso(_utcnow())),
            updated_at=str(raw.get("updated_at") or _iso(_utcnow())),
            mode=str(raw.get("mode") or "topic_bundles"),
        )


class CourseBuildStore:
    def __init__(self, root: Path, *, ttl_days: int = _TTL_DEFAULT_DAYS) -> None:
        self.root = root
        self.ttl_days = max(1, ttl_days)
        self.root.mkdir(parents=True, exist_ok=True)

    def _user_dir(self, user_id: uuid.UUID) -> Path:
        return self.root / str(user_id)

    def _build_dir(self, user_id: uuid.UUID, build_id: uuid.UUID) -> Path:
        return self._user_dir(user_id) / str(build_id)

    def create(
        self,
        *,
        user_id: uuid.UUID,
        request_payload: dict[str, Any],
        title: str,
        mode: str,
    ) -> CourseBuildMeta:
        build_id = uuid.uuid4()
        now = _iso(_utcnow())
        meta = CourseBuildMeta(
            build_id=str(build_id),
            user_id=str(user_id),
            status="running",
            stage="analyze",
            title=title.strip() or "Course draft",
            progress=0.0,
            message="Starting course build",
            chapter_total=0,
            chapters_done=0,
            error=None,
            created_at=now,
            updated_at=now,
            mode=mode,
        )
        build_dir = self._build_dir(user_id, build_id)
        build_dir.mkdir(parents=True, exist_ok=True)
        write_json(build_dir / _REQUEST, request_payload)
        write_json(build_dir / _META, meta.to_dict())
        return meta

    def exists(self, user_id: uuid.UUID, build_id: uuid.UUID) -> bool:
        return (self._build_dir(user_id, build_id) / _META).is_file()

    def load_meta(self, user_id: uuid.UUID, build_id: uuid.UUID) -> CourseBuildMeta:
        path = self._build_dir(user_id, build_id) / _META
        if not path.is_file():
            raise FileNotFoundError(f"course build not found: {build_id}")
        raw = read_json(path)
        if not isinstance(raw, dict):
            raise ValueError("invalid course build meta")
        meta = CourseBuildMeta.from_dict(raw)
        if meta.user_id != str(user_id):
            raise PermissionError("course build belongs to another user")
        return meta

    def load_request(self, user_id: uuid.UUID, build_id: uuid.UUID) -> dict[str, Any]:
        path = self._build_dir(user_id, build_id) / _REQUEST
        raw = read_json(path)
        if not isinstance(raw, dict):
            raise ValueError("invalid course build request")
        return raw

    def save_request(
        self,
        user_id: uuid.UUID,
        build_id: uuid.UUID,
        request_payload: dict[str, Any],
    ) -> None:
        write_json(self._build_dir(user_id, build_id) / _REQUEST, request_payload)

    def save_meta(self, meta: CourseBuildMeta) -> None:
        build_dir = self._build_dir(uuid.UUID(meta.user_id), uuid.UUID(meta.build_id))
        updated = CourseBuildMeta(
            build_id=meta.build_id,
            user_id=meta.user_id,
            status=meta.status,
            stage=meta.stage,
            title=meta.title,
            progress=meta.progress,
            message=meta.message,
            chapter_total=meta.chapter_total,
            chapters_done=meta.chapters_done,
            error=meta.error,
            created_at=meta.created_at,
            updated_at=_iso(_utcnow()),
            mode=meta.mode,
        )
        write_json(build_dir / _META, updated.to_dict())

    def patch_meta(
        self,
        user_id: uuid.UUID,
        build_id: uuid.UUID,
        *,
        status: CourseBuildStatus | None = None,
        stage: str | None = None,
        title: str | None = None,
        progress: float | None = None,
        message: str | None = None,
        chapter_total: int | None = None,
        chapters_done: int | None = None,
        error: str | None = None,
        clear_error: bool = False,
    ) -> CourseBuildMeta:
        meta = self.load_meta(user_id, build_id)
        next_meta = CourseBuildMeta(
            build_id=meta.build_id,
            user_id=meta.user_id,
            status=status or meta.status,
            stage=stage if stage is not None else meta.stage,
            title=title if title is not None else meta.title,
            progress=progress if progress is not None else meta.progress,
            message=message if message is not None else meta.message,
            chapter_total=chapter_total if chapter_total is not None else meta.chapter_total,
            chapters_done=chapters_done if chapters_done is not None else meta.chapters_done,
            error=None if clear_error else (error if error is not None else meta.error),
            created_at=meta.created_at,
            updated_at=meta.updated_at,
            mode=meta.mode,
        )
        self.save_meta(next_meta)
        return next_meta

    def save_analyze(
        self, user_id: uuid.UUID, build_id: uuid.UUID, payload: dict[str, Any]
    ) -> None:
        write_json(self._build_dir(user_id, build_id) / _ANALYZE, payload)

    def load_analyze(self, user_id: uuid.UUID, build_id: uuid.UUID) -> dict[str, Any] | None:
        path = self._build_dir(user_id, build_id) / _ANALYZE
        if not path.is_file():
            return None
        raw = read_json(path)
        return raw if isinstance(raw, dict) else None

    def save_compiler(
        self, user_id: uuid.UUID, build_id: uuid.UUID, payload: dict[str, object]
    ) -> None:
        write_json(self._build_dir(user_id, build_id) / _COMPILER, payload)

    def load_compiler(self, user_id: uuid.UUID, build_id: uuid.UUID) -> dict[str, object] | None:
        path = self._build_dir(user_id, build_id) / _COMPILER
        if not path.is_file():
            return None
        raw = read_json(path)
        return raw if isinstance(raw, dict) else None

    def save_blueprint(
        self, user_id: uuid.UUID, build_id: uuid.UUID, payload: dict[str, object]
    ) -> None:
        write_json(self._build_dir(user_id, build_id) / _BLUEPRINT, payload)

    def load_blueprint(self, user_id: uuid.UUID, build_id: uuid.UUID) -> dict[str, object] | None:
        path = self._build_dir(user_id, build_id) / _BLUEPRINT
        if not path.is_file():
            return None
        raw = read_json(path)
        return raw if isinstance(raw, dict) else None

    def save_topic(
        self,
        user_id: uuid.UUID,
        build_id: uuid.UUID,
        chapter_id: str,
        *,
        theories: list[dict[str, object]] | None = None,
        theory: dict[str, object] | None = None,
        quizzes: list[dict[str, object]],
        codes: list[dict[str, object]],
    ) -> None:
        safe = chapter_id.replace("/", "_").strip() or "chapter"
        theory_steps = theories if theories is not None else ([theory] if theory else [])
        write_json(
            self._build_dir(user_id, build_id) / _TOPICS / f"{safe}.json",
            {
                "chapter_id": chapter_id,
                "theory": theory_steps[0] if len(theory_steps) == 1 else None,
                "theories": theory_steps,
                "quizzes": quizzes,
                "codes": codes,
            },
        )

    def load_topic(
        self,
        user_id: uuid.UUID,
        build_id: uuid.UUID,
        chapter_id: str,
    ) -> dict[str, Any] | None:
        safe = chapter_id.replace("/", "_").strip() or "chapter"
        path = self._build_dir(user_id, build_id) / _TOPICS / f"{safe}.json"
        if not path.is_file():
            return None
        raw = read_json(path)
        return raw if isinstance(raw, dict) else None

    def _section_dir(self, user_id: uuid.UUID, build_id: uuid.UUID, chapter_id: str) -> Path:
        safe = chapter_id.replace("/", "_").strip() or "chapter"
        return self._build_dir(user_id, build_id) / _SECTIONS / safe

    def save_section_draft(
        self,
        user_id: uuid.UUID,
        build_id: uuid.UUID,
        chapter_id: str,
        *,
        index: int,
        total: int,
        content: str,
    ) -> None:
        write_json(
            self._section_dir(user_id, build_id, chapter_id) / f"{index:03d}.json",
            {"index": index, "total": total, "content": content},
        )

    def load_section_drafts(
        self,
        user_id: uuid.UUID,
        build_id: uuid.UUID,
        chapter_id: str,
    ) -> list[str]:
        folder = self._section_dir(user_id, build_id, chapter_id)
        if not folder.is_dir():
            return []
        by_index: dict[int, str] = {}
        declared_total = 0
        for path in folder.glob("*.json"):
            try:
                raw = read_json(path)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if not isinstance(raw, dict):
                continue
            index = raw.get("index")
            text = raw.get("content")
            if not isinstance(index, int) or index < 1 or not isinstance(text, str):
                continue
            if not text.strip():
                continue
            by_index[index] = text
            total = raw.get("total")
            if isinstance(total, int):
                declared_total = max(declared_total, total)
        if not by_index:
            return []
        size = max(declared_total, max(by_index))
        return [by_index.get(offset, "") for offset in range(1, size + 1)]

    def discard_section_drafts(
        self, user_id: uuid.UUID, build_id: uuid.UUID, chapter_id: str
    ) -> None:
        folder = self._section_dir(user_id, build_id, chapter_id)
        if folder.is_dir():
            shutil.rmtree(folder)

    def list_topic_ids(self, user_id: uuid.UUID, build_id: uuid.UUID) -> set[str]:
        folder = self._build_dir(user_id, build_id) / _TOPICS
        if not folder.is_dir():
            return set()
        ids: set[str] = set()
        for path in folder.glob("*.json"):
            try:
                raw = read_json(path)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if isinstance(raw, dict) and raw.get("chapter_id"):
                ids.add(str(raw["chapter_id"]))
        return ids

    def load_topics(
        self, user_id: uuid.UUID, build_id: uuid.UUID
    ) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
        folder = self._build_dir(user_id, build_id) / _TOPICS
        theory: list[dict[str, object]] = []
        quizzes: list[dict[str, object]] = []
        codes: list[dict[str, object]] = []
        if not folder.is_dir():
            return theory, quizzes, codes
        paths = sorted(folder.glob("*.json"), key=lambda p: p.name)
        for path in paths:
            try:
                raw = read_json(path)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if not isinstance(raw, dict):
                continue
            theories = raw.get("theories")
            if isinstance(theories, list) and theories:
                theory.extend(item for item in theories if isinstance(item, dict))
            else:
                step = raw.get("theory")
                if isinstance(step, dict):
                    theory.append(step)
            quiz_list = raw.get("quizzes")
            if isinstance(quiz_list, list):
                quizzes.extend(item for item in quiz_list if isinstance(item, dict))
            code_list = raw.get("codes")
            if isinstance(code_list, list):
                codes.extend(item for item in code_list if isinstance(item, dict))
        return theory, quizzes, codes

    def save_theory_step(
        self, user_id: uuid.UUID, build_id: uuid.UUID, chapter_id: str, step: dict[str, object]
    ) -> None:
        safe = chapter_id.replace("/", "_").strip() or "chapter"
        write_json(self._build_dir(user_id, build_id) / _THEORY / f"{safe}.json", step)

    def list_theory_ids(self, user_id: uuid.UUID, build_id: uuid.UUID) -> set[str]:
        folder = self._build_dir(user_id, build_id) / _THEORY
        if not folder.is_dir():
            return set()
        return {path.stem for path in folder.glob("*.json")}

    def load_theory_steps(
        self, user_id: uuid.UUID, build_id: uuid.UUID, chapter_ids: list[str]
    ) -> list[dict[str, object]]:
        folder = self._build_dir(user_id, build_id) / _THEORY
        steps: list[dict[str, object]] = []
        for chapter_id in chapter_ids:
            safe = chapter_id.replace("/", "_").strip() or "chapter"
            path = folder / f"{safe}.json"
            if not path.is_file():
                continue
            try:
                raw = read_json(path)
            except (OSError, json.JSONDecodeError, ValueError):
                continue
            if isinstance(raw, dict):
                steps.append(raw)
        return steps

    def save_quizzes(
        self, user_id: uuid.UUID, build_id: uuid.UUID, quizzes: list[dict[str, object]]
    ) -> None:
        write_json(self._build_dir(user_id, build_id) / _QUIZZES, quizzes)

    def load_quizzes(
        self, user_id: uuid.UUID, build_id: uuid.UUID
    ) -> list[dict[str, object]] | None:
        path = self._build_dir(user_id, build_id) / _QUIZZES
        if not path.is_file():
            return None
        raw = read_json(path)
        if not isinstance(raw, list):
            return None
        return [item for item in raw if isinstance(item, dict)]

    def save_codes(
        self, user_id: uuid.UUID, build_id: uuid.UUID, codes: list[dict[str, object]]
    ) -> None:
        write_json(self._build_dir(user_id, build_id) / _CODE, codes)

    def load_codes(self, user_id: uuid.UUID, build_id: uuid.UUID) -> list[dict[str, object]] | None:
        path = self._build_dir(user_id, build_id) / _CODE
        if not path.is_file():
            return None
        raw = read_json(path)
        if not isinstance(raw, list):
            return None
        return [item for item in raw if isinstance(item, dict)]

    def discard(self, user_id: uuid.UUID, build_id: uuid.UUID) -> None:
        build_dir = self._build_dir(user_id, build_id)
        if build_dir.is_dir():
            shutil.rmtree(build_dir)
        user_dir = self._user_dir(user_id)
        try:
            if user_dir.is_dir() and not any(user_dir.iterdir()):
                user_dir.rmdir()
        except OSError:
            pass

    def list_for_user(
        self, user_id: uuid.UUID, *, include_done: bool = False
    ) -> list[CourseBuildMeta]:
        self.prune_expired(user_id)
        user_dir = self._user_dir(user_id)
        if not user_dir.is_dir():
            return []
        items: list[CourseBuildMeta] = []
        for child in user_dir.iterdir():
            if not child.is_dir():
                continue
            meta_path = child / _META
            if not meta_path.is_file():
                continue
            try:
                raw = read_json(meta_path)
                if not isinstance(raw, dict):
                    continue
                meta = CourseBuildMeta.from_dict(raw)
            except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError):
                continue
            if meta.user_id != str(user_id):
                continue
            if meta.status == "done" and not include_done:
                continue
            items.append(meta)
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items

    def prune_expired(self, user_id: uuid.UUID) -> int:
        user_dir = self._user_dir(user_id)
        if not user_dir.is_dir():
            return 0
        cutoff = _utcnow() - timedelta(days=self.ttl_days)
        removed = 0
        for child in list(user_dir.iterdir()):
            if not child.is_dir():
                continue
            meta_path = child / _META
            if not meta_path.is_file():
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
                continue
            try:
                raw = read_json(meta_path)
                if not isinstance(raw, dict):
                    shutil.rmtree(child, ignore_errors=True)
                    removed += 1
                    continue
                updated = _parse_iso(str(raw.get("updated_at") or raw.get("created_at")))
            except (OSError, json.JSONDecodeError, ValueError, TypeError, KeyError):
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
                continue
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=UTC)
            if updated < cutoff:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1
        try:
            if user_dir.is_dir() and not any(user_dir.iterdir()):
                user_dir.rmdir()
        except OSError:
            pass
        return removed
