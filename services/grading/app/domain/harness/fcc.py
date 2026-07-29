from __future__ import annotations

import json

from .shared import PistonJob


def build_fcc_job(
    *,
    runtime: str,
    source: str,
    fcc_tests: list[object],
) -> PistonJob | None:
    lang = runtime.casefold().strip() or "javascript"
    runnable = _fcc_runnable_tests(fcc_tests)
    if not runnable:
        return None

    if lang in {"javascript", "js", "node", "typescript", ""}:
        return PistonJob(
            language="javascript",
            version="18.15.0",
            files=[{"name": "main.js", "content": _fcc_javascript_script(source, runnable)}],
        )
    return None


def _fcc_runnable_tests(fcc_tests: list[object]) -> list[dict[str, str]]:
    runnable: list[dict[str, str]] = []
    for item in fcc_tests:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        test_string = item.get("test_string") or item.get("testString")
        if not isinstance(test_string, str) or not test_string.strip():
            continue
        lowered = test_string.casefold()
        blocked = ("__helpers", "enzyme", "react", "document.", "window.")
        if all(token not in lowered for token in blocked):
            runnable.append(
                {
                    "text": text.strip() if isinstance(text, str) else "",
                    "test_string": test_string.strip(),
                }
            )
    return runnable


def _fcc_javascript_script(source: str, tests: list[dict[str, str]]) -> str:
    code_literal = json.dumps(source)
    tests_literal = json.dumps(tests, ensure_ascii=False)
    return f"""
const assert = require('assert');
const code = {code_literal};
const __tests = {tests_literal};

try {{
  eval(code);
}} catch (err) {{
}}

for (let i = 0; i < __tests.length; i += 1) {{
  const t = __tests[i];
  try {{
    eval(t.test_string);
  }} catch (err) {{
    const msg = (err && err.message) ? err.message : String(err);
    console.error(`FCC test ${{i}} failed: ${{msg}}`);
    if (t.text) console.error(t.text);
    process.exit(1);
  }}
}}
"""
