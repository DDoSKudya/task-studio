#!/usr/bin/env bash
# One-time developer shell setup: mise auto-activate + just.
set -euo pipefail

MISE_BIN="${HOME}/.local/bin/mise"
JUST_BIN="${HOME}/.local/bin/just"

mkdir -p "${HOME}/.local/bin"

if [[ ! -x "${MISE_BIN}" ]]; then
  echo "mise not found at ${MISE_BIN}."
  echo "Install from https://mise.jdx.dev/ then re-run this script."
  exit 1
fi

# Keep just available even when mise cache/network hiccups.
if [[ ! -x "${JUST_BIN}" ]]; then
  echo "Downloading just 1.40.0 into ~/.local/bin ..."
  curl -fsSL \
    "https://github.com/casey/just/releases/download/1.40.0/just-1.40.0-x86_64-unknown-linux-musl.tar.gz" \
    | tar -xz -C "${HOME}/.local/bin" just
  chmod +x "${JUST_BIN}"
fi

append_once() {
  local file="$1"
  local marker="$2"
  local block="$3"
  if [[ ! -e "${file}" ]]; then
    touch "${file}" || {
      echo "Cannot create ${file}. Fix ownership: sudo chown \"\$USER:\$USER\" \"${file%/*}\""
      return 1
    }
  fi
  if [[ ! -w "${file}" ]]; then
    echo "Cannot write ${file} (owned by $(stat -c '%U:%G' "${file}" 2>/dev/null || echo unknown))."
    echo "  sudo chown \"\$USER:\$USER\" \"${file}\""
    echo "  then re-run: ./scripts/setup-shell.sh"
    return 1
  fi
  if grep -Fq "${marker}" "${file}"; then
    echo "OK: ${file} already has ${marker}"
    return
  fi
  printf '\n%s\n' "${block}" >> "${file}"
  echo "Appended to ${file}"
}

BLOCK_ZSH='# mise: node, just, uv, python — available in every new terminal
export PATH="$HOME/.local/bin:$PATH"
if [ -x "$HOME/.local/bin/mise" ]; then
  eval "$("$HOME/.local/bin/mise" activate zsh)"
fi'

append_once "${HOME}/.zshrc" 'mise activate zsh' "${BLOCK_ZSH}"
append_once "${HOME}/.zprofile" 'mise activate zsh' "${BLOCK_ZSH}"

echo
echo "Installing tools from .mise.toml (includes just)..."
cd "$(dirname "$0")/.."
"${MISE_BIN}" install

# Fix root-owned mise cache leftovers from container/root runs.
if [[ -d "${HOME}/.cache/mise" ]]; then
  find "${HOME}/.cache/mise" -user root -print -quit >/dev/null 2>&1 && {
    echo "Note: some files under ~/.cache/mise are owned by root."
    echo "      Run: sudo chown -R \"\$USER:\$USER\" ~/.cache/mise ~/.local/share/mise"
  } || true
fi

echo
echo "Done. Open a new terminal (or: source ~/.zshrc) then run:"
echo "  just --list"
echo "  just up"
echo "  just web-dev"
