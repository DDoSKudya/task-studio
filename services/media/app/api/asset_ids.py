from __future__ import annotations

import re

from fastapi import HTTPException, status

SAFE_ASSET = re.compile(r"^[A-Za-z0-9._\-/]+$")
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def require_safe_asset_id(asset_id: str) -> None:
    cleaned = asset_id.lstrip("/")
    if not cleaned or ".." in cleaned or not SAFE_ASSET.fullmatch(cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid asset_id"
        )


def safe_filename(filename: str | None) -> str:
    if not filename:
        return "file.bin"
    base = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return cleaned[:120] or "file.bin"
