from __future__ import annotations

import base64
import binascii
import json
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import jsonschema
from jsonschema.exceptions import ValidationError

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "pack-schema-v1.json"
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


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: str
    message: str


def validate_manifest(manifest: dict[str, object]) -> None:
    if issues := collect_manifest_errors(manifest):
        raise ValueError(issues[0].message)


def collect_manifest_errors(manifest: dict[str, object]) -> list[ValidationIssue]:
    try:
        jsonschema.validate(instance=manifest, schema=_PACK_SCHEMA)
    except ValidationError as exc:
        return [ValidationIssue(path=_json_path(exc.absolute_path), message=exc.message)]

    issues: list[ValidationIssue] = []
    steps = manifest.get("steps")
    if not isinstance(steps, dict):
        return issues
    for step_id, step in steps.items():
        if isinstance(step, dict) and step.get("kind") == "lab":
            issues.extend(_lab_step_errors(step_id, step))
    return issues


def _lab_step_errors(step_id: str, step: dict[str, object]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    compose_file = step.get("compose_file")
    if not isinstance(compose_file, str) or not compose_file.strip():
        issues.append(
            ValidationIssue(
                path=f"steps.{step_id}.compose_file",
                message="lab step requires compose_file",
            )
        )
    checks = step.get("checks")
    if not isinstance(checks, list) or not checks:
        issues.append(
            ValidationIssue(
                path=f"steps.{step_id}.checks",
                message="lab step requires at least one check",
            )
        )
    return issues


def build_pack_archive(
    manifest: dict[str, object],
    assets: dict[str, bytes] | None = None,
) -> bytes:
    if issues := collect_manifest_errors(manifest):
        msg = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        raise ValueError(msg)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            _MANIFEST_NAME,
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
        for path, content in sorted((assets or {}).items()):
            _assert_safe_archive_path(path)
            archive.writestr(path, content)
    return buffer.getvalue()


def decode_build_assets(encoded_assets: list[tuple[str, str]]) -> dict[str, bytes]:
    assets: dict[str, bytes] = {}
    for path, content_base64 in encoded_assets:
        _assert_safe_archive_path(path)
        try:
            assets[path] = base64.b64decode(content_base64, validate=True)
        except (ValueError, binascii.Error) as exc:
            msg = f"invalid base64 for asset {path!r}"
            raise ValueError(msg) from exc
    return assets


def _assert_safe_archive_path(path: str) -> None:
    normalized = Path(path)
    if normalized.is_absolute() or ".." in normalized.parts:
        msg = f"unsafe asset path: {path}"
        raise ValueError(msg)


def _json_path(path: Sequence[str | int]) -> str:
    if not path:
        return "manifest"
    return ".".join(str(part) for part in path)


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
