#!/usr/bin/env python3
"""Снимок docs/PREVIEW.md → docs/assets/readme-preview.png (Playwright).

PREVIEW — HTML внутри .md с локальными img/svg. Chromium блокирует file://
из about:blank, поэтому локальные src/url(...) вшиваются как data: URI.

Требования:
  pip install playwright && playwright install chromium

Пример:
  python scripts/docs-capture-preview.py
  python scripts/docs-capture-preview.py --width 1280 --scale 2
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

_ATTR_URL = re.compile(
    r"""(?P<attr>\b(?:src|href))\s*=\s*(?P<q>['"])(?P<url>[^'"]+)(?P=q)""",
    re.IGNORECASE,
)
_CSS_URL = re.compile(r"""url\(\s*(?P<q>['"]?)(?P<url>[^'")\s]+)(?P=q)\s*\)""", re.IGNORECASE)
_EMBED_ATTRS = frozenset({"src"})


def _looks_like_html(text: str) -> bool:
    head = text.lstrip()[:200].lower()
    return head.startswith("<!doctype") or head.startswith("<html") or head.startswith("<div")


def _is_remote_or_special(url: str) -> bool:
    lowered = url.strip().lower()
    return not lowered or lowered.startswith(
        ("#", "data:", "mailto:", "javascript:", "http://", "https://", "file://")
    )


def _candidate_paths(raw_url: str, roots: list[Path]) -> list[Path]:
    parsed = urlparse(raw_url)
    rel = unquote(parsed.path).lstrip("/")
    if not rel:
        return []

    variants = [rel]
    if rel.startswith("docs/"):
        variants.append(rel.removeprefix("docs/"))
    else:
        variants.append(f"docs/{rel}")
    if rel.startswith("assets/"):
        variants.append(f"docs/{rel}")

    out: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        for variant in variants:
            path = (root / variant).resolve()
            if path in seen:
                continue
            seen.add(path)
            out.append(path)
    return out


def resolve_local_file(raw_url: str, roots: list[Path]) -> Path | None:
    if _is_remote_or_special(raw_url):
        return None
    for path in _candidate_paths(raw_url, roots):
        if path.is_file():
            return path
    return None


def _file_as_data_uri(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime is None:
        mime = {
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
            ".woff2": "font/woff2",
            ".woff": "font/woff",
            ".ttf": "font/ttf",
        }.get(path.suffix.lower(), "application/octet-stream")
    payload = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def rewrite_local_urls(html: str, roots: list[Path]) -> tuple[str, list[str]]:
    missing: list[str] = []

    def replace_attr(match: re.Match[str]) -> str:
        url = match.group("url")
        attr = match.group("attr").lower()
        if _is_remote_or_special(url):
            return match.group(0)
        found = resolve_local_file(url, roots)
        if found is None:
            missing.append(url)
            return match.group(0)
        if attr not in _EMBED_ATTRS:
            return match.group(0)
        uri = _file_as_data_uri(found)
        return f"{match.group('attr')}={match.group('q')}{uri}{match.group('q')}"

    def replace_css(match: re.Match[str]) -> str:
        url = match.group("url")
        if _is_remote_or_special(url):
            return match.group(0)
        found = resolve_local_file(url, roots)
        if found is None:
            missing.append(url)
            return match.group(0)
        quote = match.group("q") or '"'
        return f"url({quote}{_file_as_data_uri(found)}{quote})"

    rewritten = _ATTR_URL.sub(replace_attr, html)
    rewritten = _CSS_URL.sub(replace_css, rewritten)
    return rewritten, list(dict.fromkeys(missing))


def wrap_document(body: str) -> str:
    lowered = body.lstrip().lower()
    if lowered.startswith("<!doctype") or lowered.startswith("<html"):
        return body
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ru">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<style>html,body{margin:0;padding:0;background:#05050a;}</style>\n"
        "</head>\n"
        f"<body>\n{body}\n</body>\n"
        "</html>\n"
    )


def markdown_fallback(text: str) -> str:
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '<pre style="margin:24px;font:14px/1.45 ui-monospace,monospace;'
        f'white-space:pre-wrap;color:#e5e5e5">{escaped}</pre>'
    )


def build_html(source: Path, roots: list[Path]) -> tuple[str, list[str]]:
    text = source.read_text(encoding="utf-8")
    body = text if _looks_like_html(text) else markdown_fallback(text)
    return rewrite_local_urls(wrap_document(body), roots)


def render_png(html: str, output: Path, *, width: int, scale: float, wait_ms: int) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Нужен playwright:\n  pip install playwright\n  playwright install chromium"
        ) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(
                viewport={"width": width, "height": 900},
                device_scale_factor=scale,
            )
            page.set_content(html, wait_until="load")
            if wait_ms > 0:
                page.wait_for_timeout(wait_ms)
            page.evaluate(
                """async () => {
                  const images = [...document.images];
                  await Promise.all(images.map((img) => {
                    if (img.complete) return Promise.resolve();
                    return new Promise((resolve) => {
                      img.addEventListener('load', resolve, { once: true });
                      img.addEventListener('error', resolve, { once: true });
                    });
                  }));
                }"""
            )
            page.screenshot(path=str(output), full_page=True, type="png")
        finally:
            browser.close()


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Снимок PREVIEW.md для README")
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "docs" / "PREVIEW.md",
        help="Путь к PREVIEW.md",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=root / "docs" / "assets" / "readme-preview.png",
        help="Куда сохранить PNG",
    )
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("--wait-ms", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.input.expanduser().resolve()
    if not source.is_file():
        print(f"Файл не найден: {source}", file=sys.stderr)
        return 1

    roots = [source.parent, source.parent.parent]
    uniq_roots = [path for path in roots if path.is_dir()]
    html, missing = build_html(source, uniq_roots)
    if missing:
        print("Не найдены локальные ресурсы:", file=sys.stderr)
        for url in missing:
            print(f"  - {url}", file=sys.stderr)

    output = args.out.expanduser().resolve()
    render_png(html, output, width=args.width, scale=args.scale, wait_ms=args.wait_ms)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
