#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_PACKAGES: tuple[tuple[str, str], ...] = (
    ("python", "3.12.0"),
    ("node", "18.15.0"),
    ("go", "1.16.2"),
    ("sqlite3", "3.36.0"),
    ("typescript", "5.0.3"),
    ("bash", "5.2.0"),
)


def _request(method: str, url: str, payload: dict[str, str] | None = None) -> tuple[int, object]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: object = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = raw
        return exc.code, parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="http://piston:2000",
        help="Piston base URL (default: http://piston:2000)",
    )
    args = parser.parse_args()
    base = args.url.rstrip("/")

    status, runtimes = _request("GET", f"{base}/api/v2/runtimes")
    if status != 200 or not isinstance(runtimes, list):
        print(f"piston unreachable at {base}: HTTP {status}", file=sys.stderr)
        return 1

    installed = {
        (str(item.get("language")), str(item.get("version")))
        for item in runtimes
        if isinstance(item, dict)
    }

    for language, version in DEFAULT_PACKAGES:
        already = (language, version) in installed or (
            language == "node" and ("javascript", version) in installed
        )
        if already:
            print(f"skip {language} {version} (already installed)")
            continue
        print(f"install {language} {version}...")
        code, body = _request(
            "POST",
            f"{base}/api/v2/packages",
            {"language": language, "version": version},
        )
        if code != 200:
            print(f"  failed HTTP {code}: {body}", file=sys.stderr)
            return 1
        print(f"  ok: {body}")

    status, runtimes = _request("GET", f"{base}/api/v2/runtimes")
    if status == 200 and isinstance(runtimes, list):
        print(f"runtimes ready: {len(runtimes)}")
        for item in runtimes:
            if isinstance(item, dict):
                print(f"  - {item.get('language')} {item.get('version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
