from __future__ import annotations

import uuid
from pathlib import Path

from .errors import JobError


def staging_dir(packs_root: Path, user_id: uuid.UUID) -> Path:
    path = packs_root / "staging" / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_upload_archive(
    *,
    packs_root: Path,
    user_id: uuid.UUID,
    course_id: str,
) -> Path | None:
    if not course_id.startswith("upload:"):
        return None
    file_id = course_id.removeprefix("upload:")
    if not file_id or "/" in file_id or ".." in file_id:
        raise JobError("invalid upload course id")
    directory = packs_root / "staging" / str(user_id)
    for candidate in directory.glob(f"{file_id}.*"):
        if candidate.is_file():
            return candidate
    bare = directory / file_id
    if bare.is_file():
        return bare
    raise JobError("uploaded archive missing from staging")
