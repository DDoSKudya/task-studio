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

mkdir -p "$src/app" "$src/data" "$dst/data/sub" "$dst/.git"
printf 'new\n' >"$src/app/new.txt"
printf 'payload-keep\n' >"$src/data/.keep"
printf '{"version":"1.0.1","channel":"develop","repo":"repo","ref":"develop","archive_url":"x","archive_url_zip":"y"}\n' >"$src/studio-version.json"
printf 'keep-env\n' >"$dst/.env"
printf 'keep-env-local\n' >"$dst/.env.local"
printf 'keep-data\n' >"$dst/data/sub/data.txt"
printf 'keep-state\n' >"$dst/.studio-state.json"
printf 'keep-consumer\n' >"$dst/.studio-consumer"
printf 'keep-override\n' >"$dst/compose.override.yml"
printf 'keep-git\n' >"$dst/.git/config"
printf 'old\n' >"$dst/obsolete.txt"
printf '{"status":"available"}\n' >"$dst/.studio-update-cache.json"

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
[[ ! -e "$dst/data/data" ]]
[[ -f "$dst/.studio-state.json" ]]
[[ -f "$dst/.studio-consumer" ]]
[[ -f "$dst/compose.override.yml" ]]
[[ -f "$dst/.git/config" ]]
[[ -f "$dst/.studio-update-cache.json" ]]
grep -q 'keep-data' "$dst/data/sub/data.txt"
grep -q 'keep-env' "$dst/.env"

# Checksums ignore user cache / .env and stay stable across identical trees.
tree_a="$work/hash-a"
tree_b="$work/hash-b"
mkdir -p "$tree_a/app" "$tree_b/app"
printf 'same\n' >"$tree_a/app/x.txt"
printf 'same\n' >"$tree_b/app/x.txt"
printf 'secret\n' >"$tree_a/.env"
printf '{"status":"available"}\n' >"$tree_a/.studio-update-cache.json"
hash_a="$(
  bash -lc '
    set -euo pipefail
    source "'"$ROOT"'/scripts/lib/i18n.sh"
    source "'"$ROOT"'/scripts/lib/ui.sh"
    source "'"$ROOT"'/scripts/lib/ops.sh"
    ops_content_sha256 "$1"
  ' _ "$tree_a"
)"
hash_b="$(
  bash -lc '
    set -euo pipefail
    source "'"$ROOT"'/scripts/lib/i18n.sh"
    source "'"$ROOT"'/scripts/lib/ui.sh"
    source "'"$ROOT"'/scripts/lib/ops.sh"
    ops_content_sha256 "$1"
  ' _ "$tree_b"
)"
[[ -n "$hash_a" && "$hash_a" == "$hash_b" ]]

# Unreadable file must fail fingerprint (not silently poison the digest).
bad="$work/bad-hash"
mkdir -p "$bad/app"
printf 'x\n' >"$bad/app/x.txt"
printf 'locked\n' >"$bad/app/locked.bin"
chmod 000 "$bad/app/locked.bin"
set +e
bash -lc '
  set -euo pipefail
  source "'"$ROOT"'/scripts/lib/i18n.sh"
  source "'"$ROOT"'/scripts/lib/ui.sh"
  source "'"$ROOT"'/scripts/lib/ops.sh"
  ops_content_sha256 "$1"
' _ "$bad" >/dev/null 2>&1
fp_rc=$?
set -e
chmod 644 "$bad/app/locked.bin" || true
[[ "$fp_rc" -ne 0 ]]

echo "smoke-launcher-update.sh: OK"
