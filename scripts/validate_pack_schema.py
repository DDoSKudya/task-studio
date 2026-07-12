from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
from studio_contracts.pack import validate_pack_file

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "packages" / "contracts" / "pack-schema-v1.json"
SAMPLE_MANIFEST = ROOT / "packages" / "contracts" / "fixtures" / "sample-pack" / "manifest.json"


def main() -> int:
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        validate_pack_file(SAMPLE_MANIFEST)
    except (json.JSONDecodeError, jsonschema.SchemaError, OSError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    sys.stdout.write("ok\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
