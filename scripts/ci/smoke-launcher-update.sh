#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
work="$(mktemp -d "${TMPDIR:-/tmp}/task-studio-update.XXXXXX")"
src="$work/src"
dst="$work/dst"

cleanup() {
  rm -rf "$work"
}
trap cleanup EXIT

mkdir -p "$src/app" "$dst/data/sub" "$dst/.git"
printf 'new\n' >"$src/app/new.txt"
printf '{"version":"1.0.1","channel":"develop","repo":"repo","ref":"develop","archive_url":"x","archive_url_zip":"y"}\n' >"$src/studio-version.json"
printf 'keep-env\n' >"$dst/.env"
printf 'keep-env-local\n' >"$dst/.env.local"
printf 'keep-data\n' >"$dst/data/sub/data.txt"
printf 'keep-state\n' >"$dst/.studio-state.json"
printf 'keep-consumer\n' >"$dst/.studio-consumer"
printf 'keep-override\n' >"$dst/compose.override.yml"
printf 'keep-git\n' >"$dst/.git/config"
printf 'old\n' >"$dst/obsolete.txt"

bash -lc '
  set -euo pipefail
  source "'"$ROOT"'/scripts/lib/i18n.sh"
  source "'"$ROOT"'/scripts/lib/ui.sh"
  source "'"$ROOT"'/scripts/lib/ops.sh"
  ops_sync_payload "$1" "$2"
' _ "$src" "$dst"

[[ -f "$dst/app/new.txt" ]]
[[ ! -e "$dst/obsolete.txt" ]]
[[ -f "$dst/.env" ]]
[[ -f "$dst/.env.local" ]]
[[ -f "$dst/data/sub/data.txt" ]]
[[ -f "$dst/.studio-state.json" ]]
[[ -f "$dst/.studio-consumer" ]]
[[ -f "$dst/compose.override.yml" ]]
[[ -f "$dst/.git/config" ]]

echo "smoke-launcher-update.sh: OK"
