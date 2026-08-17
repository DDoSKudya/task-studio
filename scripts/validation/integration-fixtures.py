from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

from pydantic import ValidationError as PydanticValidationError
from studio_contracts.api.integration_schemas import ImportReport
from studio_integration_sdk.registry import AdapterModule, discover_adapters

ROOT = Path(__file__).resolve().parents[2]
MODULES_ROOT = ROOT / "integration_modules"
INTEGRATIONS_ROOT = ROOT / "services" / "integrations"


def _load_pack_builder() -> ModuleType:
    root = str(INTEGRATIONS_ROOT)
    if root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    return importlib.import_module("app.domain.pack.builder")


def _fixture_course_ids(fixtures_dir: Path) -> list[str]:
    if not fixtures_dir.is_dir():
        return []
    return sorted(path.stem.removeprefix("course_") for path in fixtures_dir.glob("course_*.json"))


def _validate_adapter(pack_builder: ModuleType, adapter: AdapterModule) -> None:
    adapter.health()
    course_ids = _fixture_course_ids(MODULES_ROOT / adapter.info.id / "fixtures")
    if not course_ids:
        raise ValueError(f"{adapter.info.id}: no fixtures found")

    for course_id in course_ids:
        pack_raw, report_raw = adapter.import_course(course_id=course_id)
        ImportReport.model_validate(report_raw)
        pack_builder.build_manifest(pack_builder.normalized_from_adapter(pack_raw))


def main() -> int:
    adapter_count = 0
    try:
        pack_builder = _load_pack_builder()
        adapters = discover_adapters(MODULES_ROOT)
        for adapter in sorted(adapters.values(), key=lambda item: item.info.id):
            _validate_adapter(pack_builder, adapter)
        adapter_count = len(adapters)
    except (ImportError, OSError, PydanticValidationError, TypeError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    sys.stdout.write(f"ok ({adapter_count} adapters)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
