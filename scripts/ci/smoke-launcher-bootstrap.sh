#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="$(mktemp -d "${TMPDIR:-/tmp}/task-studio-bootstrap.XXXXXX")"
home_dir="$work/home"
install_dir="$work/install"
archive="$work/src.tgz"
bootstrap="$work/install.sh"
desktop_dir="$home_dir/Desktop"
payload_dir="$work/task-studio-smoke"

cleanup() {
  rm -rf "$work"
}
trap cleanup EXIT

mkdir -p "$home_dir" "$desktop_dir"

python3 - <<'PY' "$ROOT" "$payload_dir"
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
payload = Path(sys.argv[2])
payload.mkdir(parents=True, exist_ok=True)

for rel in subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines():
    src = root / rel
    if not src.is_file():
        continue
    dst = payload / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
PY
tar -czf "$archive" -C "$work" "$(basename "$payload_dir")"
cp "$ROOT/scripts/install.sh" "$bootstrap"

(
  cd "$work"
  HOME="$home_dir" \
  TASK_STUDIO_DIR="$install_dir" \
  TASK_STUDIO_ARCHIVE_URL="file://$archive" \
  bash "$bootstrap" help
)

[[ -f "$install_dir/scripts/studio.sh" ]]
[[ -f "$install_dir/studio-version.json" ]]
[[ -f "$install_dir/.studio-consumer" ]]
[[ -f "$install_dir/.studio-state.json" ]]
[[ -f "$desktop_dir/task-studio.desktop" || -f "$desktop_dir/Task Studio Launcher.command" ]]

python3 - <<'PY' "$install_dir/.studio-state.json"
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["version"], "missing version"
assert "content_sha256" in data, "missing content_sha256"
PY

echo "smoke-launcher-bootstrap.sh: OK"
