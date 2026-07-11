from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import jsonschema

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "pack-schema-v1.json"
_PACK_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
_MANIFEST_NAME = "manifest.json"


@dataclass(frozen=True, slots=True)
class ParsedManifest:
    schema_version: int
    slug: str
    version: str
    title: str
    source: str
    raw: dict[str, object]


def validate_manifest(manifest: dict[str, object]) -> None:
    jsonschema.validate(instance=manifest, schema=_PACK_SCHEMA)


def validate_pack_file(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        msg = "manifest must be a JSON object"
        raise ValueError(msg)
    validate_manifest(manifest)


def parse_manifest(manifest: dict[str, object]) -> ParsedManifest:
    validate_manifest(manifest)
    return _build_parsed_manifest(manifest)


def _required_str(manifest: dict[str, object], key: str) -> str:
    if key not in manifest:
        msg = f"manifest missing {key!r}"
        raise ValueError(msg)
    value = manifest[key]
    if not isinstance(value, str):
        msg = f"manifest[{key!r}] must be a string"
        raise ValueError(msg)
    return value


def _required_int(manifest: dict[str, object], key: str) -> int:
    if key not in manifest:
        msg = f"manifest missing {key!r}"
        raise ValueError(msg)
    value = manifest[key]
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"manifest[{key!r}] must be an integer"
        raise ValueError(msg)
    return value


def _build_parsed_manifest(manifest: dict[str, object]) -> ParsedManifest:
    return ParsedManifest(
        schema_version=_required_int(manifest, "schema_version"),
        slug=_required_str(manifest, "id"),
        version=_required_str(manifest, "version"),
        title=_required_str(manifest, "title"),
        source=_manifest_source_type(manifest),
        raw=manifest,
    )


def _manifest_source_type(manifest: dict[str, object]) -> str:
    source = manifest.get("source")
    if isinstance(source, dict):
        value = source.get("type")
        if isinstance(value, str):
            return value
    return "local"


def _read_manifest(zf: zipfile.ZipFile) -> dict[str, object]:
    if _MANIFEST_NAME not in zf.namelist():
        msg = "manifest.json is missing from pack archive"
        raise ValueError(msg)
    manifest = json.loads(zf.read(_MANIFEST_NAME).decode("utf-8"))
    if not isinstance(manifest, dict):
        msg = "manifest.json must contain a JSON object"
        raise ValueError(msg)
    validate_manifest(manifest)
    return manifest


def read_manifest_from_archive(archive: bytes) -> ParsedManifest:
    with zipfile.ZipFile(BytesIO(archive)) as zf:
        return _build_parsed_manifest(_read_manifest(zf))


def extract_pack_archive(archive: bytes, dest: Path) -> ParsedManifest:
    dest.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest.resolve()

    with zipfile.ZipFile(BytesIO(archive)) as zf:
        manifest = _read_manifest(zf)
        for info in zf.infolist():
            if info.is_dir():
                continue
            target = (dest / info.filename).resolve()
            if not str(target).startswith(str(dest_resolved)):
                msg = f"unsafe path in archive: {info.filename}"
                raise ValueError(msg)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(info.filename))

    return _build_parsed_manifest(manifest)
