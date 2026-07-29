\
\
\
\
   

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
_active_service: str | None = None


def _purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


def _service_root_for(path: Path) -> Path | None:
    try:
        relative = path.resolve().relative_to(_REPO_ROOT)
    except ValueError:
        return None
    parts = relative.parts
    if len(parts) >= 2 and parts[0] == "services":
        return _REPO_ROOT / "services" / parts[1]
    return None


def _prefer_service_root(service_root: Path) -> None:
    root = str(service_root)
    while root in sys.path:
        sys.path.remove(root)
    sys.path.insert(0, root)
    tests_dir = service_root / "tests"
    if tests_dir.is_dir():
        tests = str(tests_dir)
        while tests in sys.path:
            sys.path.remove(tests)
        sys.path.insert(0, tests)


def _activate_service_for(path: Path, *, force_purge: bool) -> None:
    global _active_service
    service_root = _service_root_for(path)
    if service_root is None:
        return
    key = str(service_root)
    _prefer_service_root(service_root)
    if force_purge or _active_service != key:
        _purge_app_modules()
        _active_service = key


def pytest_collect_file(file_path, parent):  # noqa: ARG001
    _activate_service_for(Path(file_path), force_purge=True)
    return None


def pytest_runtest_setup(item) -> None:
    path = getattr(item, "path", None) or getattr(item, "fspath", None)
    if path is not None:
        _activate_service_for(Path(path), force_purge=False)
