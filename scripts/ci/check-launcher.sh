#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

fail() {
  printf 'check-launcher: %s\n' "$*" >&2
  exit 1
}

echo "==> bash -n (studio + install + lib)"
bash_files=()
for f in scripts/*.sh scripts/lib/*.sh scripts/ci/*.sh; do
  if [[ -f "$f" ]]; then
    bash_files+=("$f")
  fi
done
[[ ${#bash_files[@]} -gt 0 ]] || fail "no bash scripts found under scripts/"
for f in "${bash_files[@]}"; do
  bash -n "$f" || fail "syntax error: $f"
done

if command -v shellcheck >/dev/null 2>&1; then
  echo "==> shellcheck"
  # shellcheck disable=SC2086
  shellcheck \
    --shell=bash \
    --source-path=SCRIPTDIR \
    --severity=warning \
    --exclude=SC1090,SC1091,SC2034,SC2155,SC2164,SC2120 \
    "${bash_files[@]}"
else
  echo "==> shellcheck skipped (not installed)"
fi

echo "==> studio.cmd must be CRLF"
cmd_file=scripts/studio.cmd
[[ -f "$cmd_file" ]] || fail "missing $cmd_file"
python3 - "$cmd_file" <<'PY' || fail "$cmd_file must use CRLF line endings"
import pathlib
import sys

data = pathlib.Path(sys.argv[1]).read_bytes()
if not data:
    sys.exit(1)
sys.exit(0 if data.count(b"\n") == data.count(b"\r\n") and b"\r\n" in data else 1)
PY

echo "==> studio-version.json"
python3 - <<'PY'
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

path = Path("studio-version.json")
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    print(f"invalid JSON: {exc}", file=sys.stderr)
    sys.exit(1)

required = ("version", "channel", "repo", "ref", "archive_url", "archive_url_zip")
missing = [k for k in required if not str(data.get(k, "")).strip()]
if missing:
    print(f"missing/empty fields: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)

for key in ("archive_url", "archive_url_zip"):
    parsed = urlparse(str(data[key]))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        print(f"{key} must be an http(s) URL", file=sys.stderr)
        sys.exit(1)

print(f"ok version={data['version']} channel={data['channel']} ref={data['ref']}")
PY

echo "==> i18n key parity (i18n.sh ↔ I18n.ps1)"
python3 - <<'PY'
import re
import sys
from pathlib import Path

sh = Path("scripts/lib/i18n.sh").read_text(encoding="utf-8")
ps = Path("scripts/lib/I18n.ps1").read_text(encoding="utf-8")
sh_keys = set(re.findall(r"^\s+([a-z0-9_]+)\)\s+en=", sh, re.M))
ps_keys = set(re.findall(r"^\s+'([a-z0-9_]+)'\s*\{", ps, re.M))
only_sh = sorted(sh_keys - ps_keys)
only_ps = sorted(ps_keys - sh_keys)
if only_sh or only_ps:
    if only_sh:
        print("keys only in i18n.sh:", ", ".join(only_sh), file=sys.stderr)
    if only_ps:
        print("keys only in I18n.ps1:", ", ".join(only_ps), file=sys.stderr)
    sys.exit(1)
if not sh_keys:
    print("no i18n keys found in i18n.sh", file=sys.stderr)
    sys.exit(1)
print(f"ok {len(sh_keys)} keys match")
PY

if command -v pwsh >/dev/null 2>&1; then
  echo "==> PowerShell parse"
  pwsh -NoProfile -NonInteractive -Command '
    $ErrorActionPreference = "Stop"
    function Test-TsPsParseUtf8([string]$Path) {
      $utf8 = New-Object System.Text.UTF8Encoding $false
      $bytes = [System.IO.File]::ReadAllBytes($Path)
      if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $text = $utf8.GetString($bytes, 3, $bytes.Length - 3)
      } else {
        $text = $utf8.GetString($bytes)
      }
      $tokens = $null
      $errors = $null
      [void][System.Management.Automation.Language.Parser]::ParseInput($text, [ref]$tokens, [ref]$errors)
      return $errors
    }
    $files = @(
      "scripts/studio.ps1",
      "scripts/install.ps1"
    ) + (Get-ChildItem -Path "scripts/lib" -Filter "*.ps1" | ForEach-Object { $_.FullName })
    $failed = $false
    foreach ($path in $files) {
      $errors = Test-TsPsParseUtf8 -Path (Resolve-Path $path)
      if ($errors -and $errors.Count -gt 0) {
        $failed = $true
        Write-Host "parse errors in $path"
        $errors | ForEach-Object { Write-Host $_ }
      }
    }
    if ($failed) { exit 1 }
    Write-Host "ok $($files.Count) PowerShell files"
  '
else
  echo "==> PowerShell parse skipped (pwsh not installed)"
fi

echo "==> PowerShell scripts must have UTF-8 BOM (Windows PS 5.1)"
python3 - <<'PY' || fail "one or more .ps1 files missing UTF-8 BOM"
from pathlib import Path
import sys

bom = b"\xef\xbb\xbf"
paths = [Path("scripts/studio.ps1"), Path("scripts/install.ps1")]
paths += sorted(Path("scripts/lib").glob("*.ps1"))
missing = [str(p) for p in paths if p.is_file() and not p.read_bytes().startswith(bom)]
if missing:
    print("missing UTF-8 BOM:", ", ".join(missing), file=sys.stderr)
    raise SystemExit(1)
print(f"ok BOM on {len(paths)} files")
PY

echo "check-launcher: OK"
