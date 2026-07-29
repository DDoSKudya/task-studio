from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path


def pack_archive_asset_id(pack_id: uuid.UUID, version: str) -> str:
    safe_version = version.replace("/", "_").replace("..", "_")
    return f"packs/{pack_id}/{safe_version}/archive.zip"


def zip_pack_directory(disk_path: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(disk_path.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(disk_path).as_posix())
    return buffer.getvalue()


def multipart_body(asset_id: str, payload: bytes) -> tuple[bytes, str]:
    boundary = f"----taskstudio{uuid.uuid4().hex}"
    chunks = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="asset_id"\r\n\r\n',
        asset_id.encode() + b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="file"; filename="archive.zip"\r\n',
        b"Content-Type: application/zip\r\n\r\n",
        payload,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"
