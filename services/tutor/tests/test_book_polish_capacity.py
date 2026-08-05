from __future__ import annotations

import ast
import types
from pathlib import Path
from typing import cast


def _load_polish_module():
    module_path = (
        Path(__file__).resolve().parents[1] / "app" / "domain" / "course_from_article" / "polish.py"
    )
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module_path))
    keep = {"_is_llm_capacity_error", "_polish_skip_warning", "_polish_attempt_settings"}
    selected = cast(
        list[ast.stmt],
        [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in keep],
    )
    module = types.SimpleNamespace()
    code = compile(ast.Module(body=selected, type_ignores=[]), str(module_path), "exec")
    exec(code, module.__dict__)
    return module


def test_is_llm_capacity_error_detects_cursor_tier() -> None:
    polish = _load_polish_module()
    detail = (
        'provider rejected: {"error":{"code":"3505",'
        '"message":"request_tier_capacity_exceeded"},"raw_status_code":429}'
    )
    assert polish._is_llm_capacity_error(detail) is True


def test_is_llm_capacity_error_rejects_plain_timeout() -> None:
    polish = _load_polish_module()
    assert polish._is_llm_capacity_error("request timed out after 30s") is False


def test_polish_skip_warning_capacity_vs_generic() -> None:
    polish = _load_polish_module()
    assert (
        polish._polish_skip_warning("ch-1", 'raw_status_code":429 capacity')
        == "book polish skipped capacity: ch-1"
    )
    assert polish._polish_skip_warning("ch-2", "invalid JSON from model").startswith(
        "book polish skipped for ch-2:"
    )


def test_polish_attempt_settings_degrade_after_capacity() -> None:
    polish = _load_polish_module()
    assert polish._polish_attempt_settings(compact=False, attempt=1) == (False, 2400)
    assert polish._polish_attempt_settings(compact=False, attempt=2) == (True, 1400)
    assert polish._polish_attempt_settings(compact=False, attempt=3) == (True, 1000)
    assert polish._polish_attempt_settings(compact=True, attempt=1) == (True, 1400)
    assert polish._polish_attempt_settings(compact=True, attempt=3) == (True, 900)
