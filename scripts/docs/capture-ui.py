#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib
import os
import re
import sys
from pathlib import Path
from typing import Protocol


class _Locator(Protocol):
    def filter(self, *, has_text: re.Pattern[str] | str = ...) -> _Locator: ...

    @property
    def first(self) -> _Locator: ...

    def count(self) -> int: ...
    def click(self, *, timeout: float = ...) -> None: ...
    def scroll_into_view_if_needed(self) -> None: ...


class _Page(Protocol):
    def goto(self, url: str, *, wait_until: str = ..., timeout: float = ...) -> object: ...
    def fill(self, selector: str, value: str) -> None: ...
    def click(self, selector: str) -> None: ...
    def wait_for_timeout(self, timeout: float) -> None: ...
    def wait_for_url(self, url: str, *, timeout: float = ...) -> None: ...
    def wait_for_selector(self, selector: str, *, timeout: float = ...) -> object: ...
    def locator(self, selector: str) -> _Locator: ...
    def get_by_text(self, text: str | re.Pattern[str], *, exact: bool = ...) -> _Locator: ...
    def evaluate(self, expression: str) -> object: ...
    def screenshot(self, *, path: str, full_page: bool = ..., type: str = ...) -> bytes: ...
    @property
    def url(self) -> str: ...


PUBLIC_SHOTS: list[tuple[str, str]] = [
    ("/login", "01-login"),
    ("/login?mode=register", "02-register"),
]


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Снимки UI Task Studio для docs/")
    parser.add_argument("--base", default=os.environ.get("TASK_STUDIO_UI_URL", "http://localhost"))
    parser.add_argument(
        "--out",
        type=Path,
        default=root / "docs" / "assets" / "ui",
    )
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--scale", type=float, default=2.0)
    parser.add_argument("--wait-ms", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    try:
        sync_playwright = importlib.import_module("playwright.sync_api").sync_playwright
    except ImportError:
        print(
            "Нужен playwright:\n  pip install playwright\n  playwright install chromium",
            file=sys.stderr,
        )
        return 1

    args = parse_args()
    out: Path = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    base = str(args.base).rstrip("/")
    wait_ms = int(args.wait_ms)

    email = os.environ.get("DOCS_UI_EMAIL", "").strip()
    password = os.environ.get("DOCS_UI_PASSWORD", "").strip()

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(
                viewport={"width": int(args.width), "height": int(args.height)},
                device_scale_factor=float(args.scale),
            )
            try:
                resp = page.goto(f"{base}/", wait_until="domcontentloaded", timeout=15_000)
            except Exception as exc:
                print(f"Стек недоступен по {base}: {exc}", file=sys.stderr)
                return 2
            if resp is not None and resp.status >= 500:
                print(f"HTTP {resp.status} на {base}/", file=sys.stderr)
                return 2

            for path, name in PUBLIC_SHOTS:
                _shot(page, base, path, out / f"{name}.png", wait_ms)

            if not email or not password:
                print(
                    "DOCS_UI_EMAIL / DOCS_UI_PASSWORD не заданы — "
                    "сняты только публичные экраны (login/register).",
                    file=sys.stderr,
                )
                print(out)
                return 0

            _login(page, base, email, password, wait_ms)
            _capture_authed(page, base, out, wait_ms, email, password)
        finally:
            browser.close()

    print(out)
    return 0


def _login(page: _Page, base: str, email: str, password: str, wait_ms: int) -> None:
    page.goto(f"{base}/login", wait_until="networkidle")
    page.fill('input[type="email"], input[name="email"]', email)
    page.fill('input[type="password"], input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_url("**/catalog**", timeout=60_000)
    if wait_ms > 0:
        page.wait_for_timeout(wait_ms)


def _capture_authed(
    page: _Page,
    base: str,
    out: Path,
    wait_ms: int,
    email: str,
    password: str,
) -> None:
    _shot(page, base, "/catalog", out / "11-catalog.png", wait_ms)

    page.goto(f"{base}/catalog?tab=discover", wait_until="networkidle")
    if wait_ms > 0:
        page.wait_for_timeout(wait_ms)
    _save(page, out / "12-catalog-find.png")

    create = page.locator("button, a").filter(
        has_text=re.compile(r"CREATE FROM ARTICLES|Create from articles|Создать из", re.I),
    )
    if create.count():
        create.first.click()
        page.wait_for_timeout(max(wait_ms, 1200))
        _save(page, out / "12b-catalog-create.png")

    _shot(page, base, "/analytics", out / "13-analytics.png", wait_ms)
    _shot(page, base, "/settings", out / "14-settings.png", wait_ms)

    _open_settings_section(page, re.compile(r"AI AGENT|AI agent|ИИ", re.I))
    _redact_secrets(page)
    _save(page, out / "14b-settings-ai.png")

    _open_settings_section(page, re.compile(r"EDITOR|Editor|Редактор", re.I))
    _save(page, out / "14c-settings-editor.png")

    _open_settings_section(page, re.compile(r"STEPIK|Stepik", re.I))
    _redact_secrets(page)
    _save(page, out / "14d-settings-integration.png")

    packs = page.evaluate(
        """async () => {
          const r = await fetch('/api/v1/catalog/packs', {credentials:'include'});
          if (!r.ok) return [];
          return await r.json();
        }""",
    )
    if isinstance(packs, list) and packs:
        pack_id = str(packs[0].get("id") or "")
        if pack_id:
            _shot(page, base, f"/catalog/{pack_id}", out / "15-catalog-detail.png", wait_ms)

    page.goto(f"{base}/catalog", wait_until="networkidle")
    if wait_ms > 0:
        page.wait_for_timeout(wait_ms)
    session_link = page.locator('a[href*="/sessions/"]').first
    if session_link.count():
        session_link.click()
        page.wait_for_url("**/sessions/**", timeout=60_000)
        page.wait_for_timeout(max(wait_ms, 1500))
        _save(page, out / "16-session.png")
        page.evaluate("window.scrollTo(0, 700)")
        page.wait_for_timeout(400)
        _save(page, out / "16b-session-actions.png", full_page=False)

    page.goto(f"{base}/pack-studio/login", wait_until="networkidle")
    if wait_ms > 0:
        page.wait_for_timeout(wait_ms)
    _save(page, out / "21-pack-studio-login.png")
    page.fill('input[type="email"], input[name="email"]', email)
    page.fill('input[type="password"], input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(max(wait_ms, 2000))
    if "/pack-studio" in page.url:
        _save(page, out / "20-pack-studio.png")
        validate = page.get_by_text("Validate", exact=False)
        if validate.count():
            validate.first.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            _save(page, out / "20b-pack-studio-actions.png", full_page=False)


def _open_settings_section(page: _Page, pattern: re.Pattern[str]) -> None:
    btn = page.locator("button").filter(has_text=pattern)
    if btn.count():
        btn.first.click()
        page.wait_for_timeout(1000)


def _redact_secrets(page: _Page) -> None:

    page.evaluate(
        """() => {
          const emailRe = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}/gi;
          const maskEmail = 'docs@example.com';
          const keepPageTitle = /^(CATALOG|SETTINGS|ANALYTICS|PACK|LOGIN|SESSIONS?)/i;

          for (const el of document.querySelectorAll('input, textarea')) {
            const t = (el.type || '').toLowerCase();
            const meta = (
              (el.name || '') + ' ' + (el.id || '') + ' ' + (el.placeholder || '')
            ).toLowerCase();
            const looksSecret = (
              t === 'password'
              || meta.includes('secret')
              || meta.includes('token')
              || meta.includes('password')
              || meta.includes('client')
              || meta.includes('key')
            );
            const opaque = el.value && el.value.length > 16
              && /^[A-Za-z0-9_\\-.=]+$/.test(el.value);
            if (looksSecret || opaque || (el.value || '').match(emailRe)) {
              el.value = t === 'email' || meta.includes('email') ? maskEmail : '';
              el.setAttribute('value', el.value);
              el.dispatchEvent(new Event('input', { bubbles: true }));
            }
          }

          for (const el of document.querySelectorAll('.user-avatar')) {
            el.textContent = 'XX';
          }
          for (const el of document.querySelectorAll('.user-card-name')) {
            el.textContent = maskEmail;
          }

          // Названия курсов / тем / шагов — не попадают в публичные docs PNG
          const titleSelectors = [
            '.lib-card-title',
            '.lib-card-mark',
            '.ax-weak-title',
            '.ax-weak-meta',
            '.ax-feed-title',
            '.catalog-pack-title',
            '.session-lesson-title',
            '.stepik-module-title',
            '.stepik-lesson-title',
            '[data-docs-redact="title"]',
          ];
          let n = 1;
          for (const sel of titleSelectors) {
            for (const el of document.querySelectorAll(sel)) {
              const text = (el.textContent || '').trim();
              if (!text || text.length < 2) continue;
              if (keepPageTitle.test(text)) continue;
              if (el.classList.contains('lib-card-mark')) {
                el.textContent = 'E';
              } else if (el.classList.contains('ax-weak-meta')) {
                el.textContent = 'TOPIC: EXAMPLE-' + n;
              } else if (
                el.classList.contains('session-lesson-title')
                || el.classList.contains('stepik-lesson-title')
                || el.classList.contains('stepik-module-title')
              ) {
                el.textContent = 'Example step ' + n;
              } else {
                el.textContent = 'Example course ' + n;
              }
              n += 1;
            }
          }

          // Заголовок страницы курса / сессии (не CATALOG / SETTINGS / …)
          for (const el of document.querySelectorAll('h1.page-title')) {
            const text = (el.textContent || '').trim();
            if (text && text.length > 2 && !keepPageTitle.test(text)) {
              el.textContent = 'Example course';
            }
          }

          const walk = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            null,
          );
          let node = walk.nextNode();
          while (node) {
            const text = node.nodeValue || '';
            if (text.match(emailRe)) {
              node.nodeValue = text.replace(emailRe, maskEmail);
            }
            node = walk.nextNode();
          }
        }""",
    )
    page.wait_for_timeout(200)


def _shot(page: _Page, base: str, path: str, dest: Path, wait_ms: int) -> None:
    page.goto(f"{base}{path}", wait_until="networkidle")
    if wait_ms > 0:
        page.wait_for_timeout(wait_ms)
    _save(page, dest)


def _save(page: _Page, dest: Path, *, full_page: bool = True) -> None:
    page.evaluate(
        """() => {
          for (const el of document.querySelectorAll(
            '#nuxt-devtools-container, .nuxt-devtools-frame, nuxt-devtools-frame'
          )) el.remove();
        }""",
    )
    _redact_secrets(page)
    page.screenshot(path=str(dest), full_page=full_page, type="png")
    print(dest)


if __name__ == "__main__":
    raise SystemExit(main())
