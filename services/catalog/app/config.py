from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CatalogSettings:
    packs_root: Path
    max_upload_bytes: int
    media_service_url: str


def _env_int(name: str, default: int) -> int:
    # Compose may set VAR="" when interpolation misses; getenv default then does not apply.
    raw = os.getenv(name)
    if raw is None:
        return default
    text = raw.strip()
    if not text:
        return default
    try:
        return int(text)
    except ValueError:
        return default


def load_settings() -> CatalogSettings:
    packs_root = Path(os.getenv("PACKS_ROOT", "/data/packs"))
    max_upload_mb = _env_int("PACK_MAX_UPLOAD_MB", 500)
    return CatalogSettings(
        packs_root=packs_root,
        max_upload_bytes=max_upload_mb * 1024 * 1024,
        media_service_url=os.getenv("MEDIA_SERVICE_URL", "").rstrip("/"),
    )
