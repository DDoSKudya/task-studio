#!/usr/bin/env bash
set -euo pipefail

REPO_BRANCH="${TASK_STUDIO_BRANCH:-develop}"
ARCHIVE_URL="${TASK_STUDIO_ARCHIVE_URL:-https://codeload.github.com/DDoSKudya/task-studio/tar.gz/refs/heads/${REPO_BRANCH}}"
INSTALL_DIR="${TASK_STUDIO_DIR:-$HOME/task-studio}"
COMPOSE_FILE="deploy/docker-compose.yml"

TS_UI_LANG=en
_ts_boot_detect_lang() {
  local loc="${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}"
  if [[ -z "$loc" || "$loc" == "C" || "$loc" == "POSIX" ]]; then
    if [[ "$(uname -s 2>/dev/null || true)" == "Darwin" ]] && command -v defaults >/dev/null 2>&1; then
      loc="$(defaults read -g AppleLocale 2>/dev/null || true)"
    fi
  fi
  loc="$(printf '%s' "$loc" | tr '[:upper:]' '[:lower:]')"
  case "$loc" in
    ru|ru_*|ru.*|*.ru|ru@*|*"ru_ru"*) TS_UI_LANG=ru ;;
    *) TS_UI_LANG=en ;;
  esac
}
_ts_boot_detect_lang

_t() {
  local key="$1"; shift || true
  local en="" ru=""
  case "$key" in
    err) en="Error: %s"; ru="Ошибка: %s" ;;
    downloading) en="Downloading Task Studio Launcher into %s …"; ru="Скачивание Task Studio Launcher в %s …" ;;
    updating) en="Updating existing install…"; ru="Обновление существующей установки…" ;;
    err_curl) en="curl not found."; ru="curl не найден." ;;
    err_tar) en="tar not found."; ru="tar не найден." ;;
    err_download) en="Could not download Task Studio archive."; ru="Не удалось скачать архив Task Studio." ;;
    err_unpack) en="Could not unpack Task Studio archive."; ru="Не удалось распаковать архив Task Studio." ;;
    err_layout) en="Downloaded archive has unexpected layout."; ru="Скачанный архив имеет неожиданный формат." ;;
    studio_missing) en="studio.sh not found under %s/scripts"; ru="studio.sh не найден в %s/scripts" ;;
    shortcuts) en="Installing console and desktop shortcut…"; ru="Установка консоли и ярлыка на рабочий стол…" ;;
    shortcut_warn) en="Warning: could not create desktop shortcut (you can still run: bash %s/scripts/studio.sh)."; ru="Предупреждение: не удалось создать ярлык (можно запустить: bash %s/scripts/studio.sh)." ;;
    starting) en="Starting Task Studio Launcher…"; ru="Запуск Task Studio Launcher…" ;;
    *) en="$key"; ru="$key" ;;
  esac
  local text="$en"
  [[ "$TS_UI_LANG" == "ru" ]] && text="$ru"
  # shellcheck disable=SC2059
  printf "$text\n" "$@"
}

die() { printf '%s\n' "$*" >&2; exit 1; }
info() { printf '%s\n' "$*"; }

resolve_install_root() {
  local self="${BASH_SOURCE[0]:-}"
  if [[ -n "$self" && -f "$self" ]]; then
    local here
    here="$(cd "$(dirname "$self")" && pwd)"
    if [[ -f "$here/studio.sh" ]]; then
      printf '%s\n' "$(cd "$here/.." && pwd -P)"
      return 0
    fi
  fi
  if [[ -f "$COMPOSE_FILE" && -f "scripts/studio.sh" ]]; then
    pwd -P
    return 0
  fi
  if [[ -f "$INSTALL_DIR/scripts/studio.sh" ]]; then
    cd "$INSTALL_DIR" && pwd -P
    return 0
  fi
  return 1
}

download_studio() {
  info "$(_t downloading "$INSTALL_DIR")" >&2
  command -v curl >/dev/null 2>&1 || die "$(_t err_curl)"
  command -v tar >/dev/null 2>&1 || die "$(_t err_tar)"
  mkdir -p "$(dirname "$INSTALL_DIR")"
  if [[ -d "$INSTALL_DIR" ]]; then
    info "$(_t updating)" >&2
  fi
  local work archive extract payload
  work="$(mktemp -d "${TMPDIR:-/tmp}/task-studio-bootstrap.XXXXXX")"
  archive="$work/src.tgz"
  extract="$work/extract"
  mkdir -p "$extract"
  if ! curl -fsSL --connect-timeout 15 --max-time 600 "$ARCHIVE_URL" -o "$archive"; then
    rm -rf "$work"
    die "$(_t err_download)"
  fi
  if ! tar -xzf "$archive" -C "$extract"; then
    rm -rf "$work"
    die "$(_t err_unpack)"
  fi
  payload="$(find "$extract" -mindepth 1 -maxdepth 1 -type d | head -1)"
  if [[ -z "$payload" || ! -f "$payload/scripts/studio.sh" ]]; then
    rm -rf "$work"
    die "$(_t err_layout)"
  fi
  rm -rf "$INSTALL_DIR"
  mkdir -p "$(dirname "$INSTALL_DIR")"
  mv "$payload" "$INSTALL_DIR"
  rm -rf "$work"
  cd "$INSTALL_DIR" && pwd -P
}

is_consumer_install_dir() {
  local root="$1"
  local want
  want="$(cd "$INSTALL_DIR" 2>/dev/null && pwd -P || printf '%s' "$INSTALL_DIR")"
  [[ "$root" == "$want" ]]
}

remove_bootstrap_scripts() {
  local root="$1"
  is_consumer_install_dir "$root" || return 0
  rm -f "$root/scripts/install.sh" "$root/scripts/install.ps1" 2>/dev/null || true
}

root="$(resolve_install_root || true)"
if [[ -z "${root:-}" ]]; then
  root="$(download_studio)"
fi

[[ -f "$root/scripts/studio.sh" ]] || die "$(_t studio_missing "$root")"

cd "$root"
# shellcheck source=lib/i18n.sh
if [[ -f "$root/scripts/lib/i18n.sh" ]]; then
  # shellcheck disable=SC1091
  source "$root/scripts/lib/i18n.sh"
  ts_detect_lang
fi
# shellcheck source=lib/desktop.sh
source "$root/scripts/lib/desktop.sh"

info "$(ts_t boot_shortcuts 2>/dev/null || _t shortcuts)"
ensure_script_permissions "$root"
if [[ "$(uname -s)" != "Darwin" ]]; then
  /bin/chmod u+rwx,go+rx "$root/scripts/studio.sh" 2>/dev/null || true
fi
create_desktop_shortcuts "$root" || info "$(ts_t boot_shortcut_warn "$root" 2>/dev/null || _t shortcut_warn "$root")"

remove_bootstrap_scripts "$root"

if is_consumer_install_dir "$root"; then
  : >"$root/.studio-consumer"
  if [[ -f "$root/studio-version.json" ]] && command -v python3 >/dev/null 2>&1; then
    ver="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1],encoding="utf-8")).get("version",""))' "$root/studio-version.json" 2>/dev/null || true)"
    if [[ -n "${ver:-}" ]]; then
      printf '{\n  "version": "%s",\n  "content_sha256": ""\n}\n' "$ver" >"$root/.studio-state.json"
    fi
  fi
fi

info "$(ts_t boot_starting 2>/dev/null || _t starting)"
export TS_UI_LANG
exec bash "$root/scripts/studio.sh" "$@"
