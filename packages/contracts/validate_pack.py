from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

import jsonschema

_SCHEMA_PATH = Path(__file__).with_name("pack-schema-v1.json")
_PACK_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _stderr() -> TextIO:
    stderr = sys.stderr
    if stderr is None:
        msg = "stderr is unavailable"
        raise RuntimeError(msg)
    return stderr


def _stdout() -> TextIO:
    stdout = sys.stdout
    if stdout is None:
        msg = "stdout is unavailable"
        raise RuntimeError(msg)
    return stdout


def _write_stderr(message: str) -> None:
    _stderr().write(f"{message}\n")


def validate_pack(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=manifest, schema=_PACK_SCHEMA)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        script = Path(sys.argv[0]).name
        _write_stderr(f"usage: {script} PATH")
        return 2

    path = Path(args[0])
    if not path.is_file():
        _write_stderr(f"file not found: {path}")
        return 1

    try:
        validate_pack(path)
    except (json.JSONDecodeError, jsonschema.ValidationError) as exc:
        _write_stderr(str(exc))
        return 1

    _stdout().write("ok\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
