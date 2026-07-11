from __future__ import annotations

import io
import zipfile
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
SAMPLE_PACK_DIR = FIXTURES_DIR / "sample-pack"


def build_sample_pack_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in SAMPLE_PACK_DIR.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(SAMPLE_PACK_DIR).as_posix())
    return buffer.getvalue()
