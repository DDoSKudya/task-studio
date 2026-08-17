#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys

_CHANNEL = {
    "alpha": 1,
    "beta": 2,
    "rc": 3,
    "ga": 9,
}

_SEMVER = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<pre>alpha|beta|rc)(?:\.(?P<n>\d+))?)?"
    r"(?:\+(?P<meta>[0-9A-Za-z.-]+))?$",
    re.IGNORECASE,
)


def parse_version(raw: str) -> tuple[int, int, int, str, int]:
    match = _SEMVER.match(raw.strip())
    if not match:
        raise ValueError(f"unsupported version {raw!r}; expected e.g. 1.1.0-beta.1 or 1.1.0")
    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))
    pre = (match.group("pre") or "ga").lower()
    n_raw = match.group("n")
    n = int(n_raw) if n_raw else 1
    if not 1 <= n <= 999:
        raise ValueError("iteration n must be 1..999")
    return major, minor, patch, pre, n


def compute_build(major: int, minor: int, patch: int, channel: str, n: int) -> int:
    code = _CHANNEL[channel]
    return major * 100_000_000 + minor * 1_000_000 + patch * 10_000 + code * 1_000 + n


def format_semver(major: int, minor: int, patch: int, channel: str, n: int) -> str:
    core = f"{major}.{minor}.{patch}"
    if channel == "ga":
        return core
    return f"{core}-{channel}.{n}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "version",
        help="SemVer string, e.g. 1.1.0-beta.1 or 1.0.0-alpha",
    )
    args = parser.parse_args(argv)
    try:
        major, minor, patch, channel, n = parse_version(args.version)
        build = compute_build(major, minor, patch, channel, n)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    display = format_semver(major, minor, patch, channel, n)
    print(f"version={display} build={build} channel={channel} n={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
