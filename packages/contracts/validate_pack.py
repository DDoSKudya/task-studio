from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
from studio_contracts.packs.pack import validate_pack_file

__all__ = ["validate_pack_file"]


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        script = Path(sys.argv[0]).name
        sys.stderr.write(f"usage: {script} PATH\n")
        return 2

    path = Path(args[0])
    if not path.is_file():
        sys.stderr.write(f"file not found: {path}\n")
        return 1

    try:
        validate_pack_file(path)
    except (json.JSONDecodeError, jsonschema.ValidationError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    sys.stdout.write("ok\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
