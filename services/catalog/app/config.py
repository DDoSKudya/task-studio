from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CatalogSettings:
    packs_root: Path
    max_upload_bytes: int


def load_settings() -> CatalogSettings:
    packs_root = Path(os.getenv("PACKS_ROOT", "/data/packs"))
    max_upload_mb = int(os.getenv("PACK_MAX_UPLOAD_MB", "500"))
    return CatalogSettings(
        packs_root=packs_root,
        max_upload_bytes=max_upload_mb * 1024 * 1024,
    )
