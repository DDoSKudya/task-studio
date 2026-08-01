#!/usr/bin/env python3
"""Remove human comments; keep shebang / tool directives. Shell/PS: full-line only."""

from __future__ import annotations

import io
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    ".nuxt",
    ".output",
    "__pycache__",
    "data",
    ".cursor",
}

KEEP_PY = re.compile(
    r"^(?:"
    r"type:\s*ignore\b|noqa\b|pragma:\s*|pylint:\s*|ruff:\s*|pyright:\s*|"
    r"fmt:\s*|isort:\s*|mypy:\s*|nosec\b|coding[:=]|-\*-|"
    r"region\b|endregion\b"
    r")",
    re.I,
)
KEEP_SH = re.compile(r"^(?:shellcheck\b|sc\d+\b)", re.I)
KEEP_PS = re.compile(r"^Requires\b", re.I)
KEEP_JS_LINE = re.compile(
    r"^(?:"
    r"eslint-disable|eslint-enable|prettier-ignore|ts-ignore|ts-nocheck|"
    r"ts-expect-error|ts-check|@ts-|istanbul ignore|c8 ignore|"
    r"webpackChunkName|vite-ignore|sourceMappingURL"
    r")",
    re.I,
)
KEEP_DOCKER = re.compile(r"^syntax\s*=", re.I)
KEEP_JUST = re.compile(r"^!", re.I)
KEEP_NEVER = re.compile(r"(?!)")


def under_skip(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def strip_python_comments(text: str) -> str:
    """Remove all # comments via tokenize; keep shebang/encoding/tool directives."""
    result: list[str] = []
    last_lineno = -1
    last_col = 0
    readline = io.StringIO(text).readline
    try:
        tokens = list(tokenize.generate_tokens(readline))
    except tokenize.TokenError:
        return text
    for tok in tokens:
        token_type = tok.type
        token_string = tok.string
        start_line, start_col = tok.start
        end_line, end_col = tok.end
        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            result.append(" " * (start_col - last_col))
        if token_type == tokenize.COMMENT:
            body = token_string.lstrip("#").strip()
            if token_string.startswith("#!") or KEEP_PY.search(body):
                result.append(token_string)
        else:
            result.append(token_string)
        last_col = end_col
        last_lineno = end_line
    out = "".join(result)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    if text.endswith("\n") and not out.endswith("\n"):
        out += "\n"
    return out


def strip_ps_block_comments(text: str) -> str:
    """Remove PowerShell <# ... #> blocks (not inside strings)."""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch in "\"'":
            quote = ch
            out.append(ch)
            i += 1
            while i < n:
                c = text[i]
                out.append(c)
                if c == "`" and i + 1 < n:
                    out.append(text[i + 1])
                    i += 2
                    continue
                if c == quote:
                    i += 1
                    break
                i += 1
            continue
        if ch == "<" and nxt == "#":
            j = text.find("#>", i + 2)
            if j < 0:
                break
            i = j + 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def strip_full_hash_lines(text: str, keep: re.Pattern[str], *, allow_shebang: bool) -> str:
    out: list[str] = []
    for i, line in enumerate(text.splitlines(keepends=True)):
        raw = line.rstrip("\r\n")
        ending = line[len(raw) :]
        stripped = raw.lstrip()
        if allow_shebang and i == 0 and stripped.startswith("#!"):
            out.append(line)
            continue
        if stripped.startswith("#"):
            body = stripped.lstrip("#").strip()
            if keep.search(body):
                out.append(line)
            continue
        out.append(raw + ending)
    result = "".join(out)
    result = re.sub(r"\n{3,}", "\n\n", result)
    if text.endswith("\n") and not result.endswith("\n"):
        result += "\n"
    return result


def strip_js_full_line_and_blocks(text: str) -> str:
    """Remove // full-line comments and /* */ blocks (not strings). Keep directive comments."""
    out: list[str] = []
    i = 0
    n = len(text)
    line_start = True
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if ch == "\n":
            out.append(ch)
            line_start = True
            i += 1
            continue
        if ch in " \t" and line_start:
            j = i
            while j < n and text[j] in " \t":
                j += 1
            if j + 1 < n and text[j : j + 2] == "//":
                rest = text[j + 2 :].split("\n", 1)[0].strip()
                if KEEP_JS_LINE.search(rest):
                    while i < n and text[i] != "\n":
                        out.append(text[i])
                        i += 1
                    line_start = False
                    continue
                while i < n and text[i] != "\n":
                    i += 1
                continue
            out.append(ch)
            i += 1
            continue
        if line_start and ch == "/" and nxt == "/":
            rest = text[i + 2 :].split("\n", 1)[0].strip()
            if KEEP_JS_LINE.search(rest):
                while i < n and text[i] != "\n":
                    out.append(text[i])
                    i += 1
                continue
            while i < n and text[i] != "\n":
                i += 1
            continue
        line_start = False
        if ch in "\"'`":
            quote = ch
            out.append(ch)
            i += 1
            while i < n:
                c = text[i]
                out.append(c)
                if c == "\\" and i + 1 < n:
                    out.append(text[i + 1])
                    i += 2
                    continue
                if c == quote:
                    i += 1
                    break
                i += 1
            continue
        if ch == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            if j < 0:
                break
            body = text[i + 2 : j].strip()
            first = body.split("\n", 1)[0].strip()
            if body.startswith("!") or KEEP_JS_LINE.search(first):
                out.append(text[i : j + 2])
            i = j + 2
            continue
        out.append(ch)
        i += 1
    result = "".join(out)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def strip_vue(text: str) -> str:
    pattern = re.compile(r"(<script\b[^>]*>)(.*?)(</script>)", re.I | re.S)

    def repl(m: re.Match[str]) -> str:
        return m.group(1) + strip_js_full_line_and_blocks(m.group(2)) + m.group(3)

    return pattern.sub(repl, text)


def process_file(path: Path) -> bool:
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    name = path.name.lower()
    suf = path.suffix.lower()
    if suf == ".py":
        new = strip_python_comments(text)
    elif suf == ".ps1":
        new = strip_full_hash_lines(strip_ps_block_comments(text), KEEP_PS, allow_shebang=False)
    elif suf == ".sh":
        new = strip_full_hash_lines(text, KEEP_SH, allow_shebang=True)
    elif suf in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        new = strip_js_full_line_and_blocks(text)
    elif suf == ".vue":
        new = strip_vue(text)
    elif name == "dockerfile" or name.startswith("dockerfile."):
        new = strip_full_hash_lines(text, KEEP_DOCKER, allow_shebang=False)
    elif name == "justfile":
        new = strip_full_hash_lines(text, KEEP_JUST, allow_shebang=True)
    elif suf in {".yml", ".yaml"}:
        new = strip_full_hash_lines(text, KEEP_NEVER, allow_shebang=False)
    else:
        return False
    if new == text:
        return False
    data = new.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)
    return True


def iter_targets() -> list[Path]:
    roots = [
        ROOT / "scripts",
        ROOT / "services",
        ROOT / "packages",
        ROOT / "apps",
        ROOT / "deploy",
    ]
    exts = {
        ".py",
        ".ps1",
        ".sh",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".vue",
        ".yml",
        ".yaml",
    }
    paths: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or under_skip(path):
                continue
            if path.name == "strip-human-comments.py":
                continue
            name = path.name.lower()
            suf = path.suffix.lower()
            if suf in exts or name == "dockerfile" or name.startswith("dockerfile."):
                paths.append(path)
    justfile = ROOT / "justfile"
    if justfile.is_file():
        paths.append(justfile)
    return paths


def main() -> int:
    changed = 0
    scanned = 0
    for path in iter_targets():
        scanned += 1
        if process_file(path):
            changed += 1
            print(path.relative_to(ROOT))
    print(f"scanned={scanned} changed={changed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
