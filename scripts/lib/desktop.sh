# Create desktop shortcuts (Linux / macOS). Call with repo root as $1.

desktop_dir() {
  local d
  if command -v xdg-user-dir >/dev/null 2>&1; then
    d="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
  fi
  if [[ -n "${d:-}" && -d "$d" ]]; then
    printf '%s\n' "$d"
    return
  fi
  if [[ -d "$HOME/Desktop" ]]; then
    printf '%s\n' "$HOME/Desktop"
    return
  fi
  printf '%s\n' "$HOME/Desktop"
}

ensure_script_permissions() {
  local root="$1"
  local f
  for f in \
    "$root/scripts/studio.sh" \
    "$root/scripts/install.sh" \
    "$root/scripts/studio.cmd"
  do
    if [[ -f "$f" ]]; then
      /bin/chmod u+rwx,go+rx "$f" 2>/dev/null || chmod u+rwx,go+rx "$f" 2>/dev/null || true
    fi
  done
  # macOS Gatekeeper: drop quarantine on console entry so double-click / Terminal works.
  if command -v xattr >/dev/null 2>&1; then
    xattr -dr com.apple.quarantine "$root/scripts" 2>/dev/null || true
    xattr -d com.apple.quarantine "$root/scripts/studio.sh" 2>/dev/null || true
  fi
}

resolve_bash() {
  if [[ -x /bin/bash ]]; then
    printf '%s\n' /bin/bash
  elif [[ -x /usr/bin/bash ]]; then
    printf '%s\n' /usr/bin/bash
  elif command -v bash >/dev/null 2>&1; then
    command -v bash
  else
    printf '%s\n' bash
  fi
}

remove_desktop_shortcuts() {
  local desk
  desk="$(desktop_dir)"
  case "$(uname -s)" in
    Darwin)
      rm -f "$desk/Task Studio.command" \
        "$desk/Task Studio Launcher.command" \
        "$desk/Task Studio — Start.command" \
        "$desk/Task Studio — Stop.command" \
        "$desk/Task Studio — Uninstall.command" \
        "$desk/Task Studio Launcher — Uninstall.command" \
        "$desk/Task Studio Launcher — Удаление.command" 2>/dev/null || true
      ;;
    *)
      rm -f "$desk/task-studio.desktop" \
        "$desk/task-studio-start.desktop" \
        "$desk/task-studio-stop.desktop" \
        "$desk/task-studio-uninstall.desktop" 2>/dev/null || true
      ;;
  esac
}

create_desktop_shortcuts() {
  local root="$1"
  local desk icon_png studio_sh bash_bin
  desk="$(desktop_dir)"
  mkdir -p "$desk" 2>/dev/null || true
  if [[ ! -w "$desk" ]]; then
    if declare -f ts_t >/dev/null 2>&1; then
      printf '%s\n' "$(ts_t warn_desktop_unwritable "$desk")" >&2
    else
      printf 'Cannot write to desktop directory: %s\n' "$desk" >&2
    fi
    return 1
  fi
  ensure_script_permissions "$root"
  icon_png="$root/docs/assets/brand/task-studio.png"
  [[ -f "$icon_png" ]] || icon_png="$root/docs/assets/logo.png"
  studio_sh="$root/scripts/studio.sh"
  bash_bin="$(resolve_bash)"

  local main_name="Task Studio Launcher"
  local comment="Task Studio Launcher"
  if declare -f ts_t >/dev/null 2>&1; then
    main_name="$(ts_t shortcut_main)"
    comment="$(ts_t shortcut_comment)"
  fi

  # Single console entry — uninstall lives in the launcher menu.
  case "$(uname -s)" in
    Darwin)
      _write_macos_command "$desk/${main_name}.command" "$studio_sh" "$icon_png" "$bash_bin"
      # Remove legacy / obsolete shortcut names from older installs.
      rm -f "$desk/Task Studio.command" \
        "$desk/Task Studio — Uninstall.command" \
        "$desk/Task Studio Launcher — Uninstall.command" \
        "$desk/Task Studio Launcher — Удаление.command" 2>/dev/null || true
      if [[ "$main_name" != "Task Studio Launcher" ]]; then
        rm -f "$desk/Task Studio Launcher.command" 2>/dev/null || true
      fi
      if declare -f ts_t >/dev/null 2>&1; then
        local uname_legacy
        uname_legacy="$(ts_t shortcut_uninstall 2>/dev/null || true)"
        if [[ -n "$uname_legacy" && "$uname_legacy" != "$main_name" ]]; then
          rm -f "$desk/${uname_legacy}.command" 2>/dev/null || true
        fi
      fi
      ;;
    *)
      _write_linux_desktop "$desk/task-studio.desktop" \
        "$main_name" "$studio_sh" "$icon_png" "$root" "$bash_bin" "$comment"
      rm -f "$desk/task-studio-uninstall.desktop" 2>/dev/null || true
      ;;
  esac
  # Clean legacy Start/Stop/Uninstall shortcuts from older installs
  remove_legacy_start_stop_shortcuts "$desk"
  if declare -f ts_t >/dev/null 2>&1; then
    printf '%s\n' "$(ts_t shortcuts_created "$desk")"
  else
    printf 'Shortcuts: %s\n' "$desk"
  fi
}

remove_legacy_start_stop_shortcuts() {
  local desk="$1"
  rm -f "$desk/Task Studio — Start.command" "$desk/Task Studio — Stop.command" \
    "$desk/task-studio-start.desktop" "$desk/task-studio-stop.desktop" \
    "$desk/task-studio-uninstall.desktop" 2>/dev/null || true
}

_write_linux_desktop() {
  local path="$1" name="$2" exec_path="$3" icon="$4" root="$5" bash_bin="$6"
  local comment="${7:-Task Studio Launcher}"
  cat >"$path" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$name
Comment=$comment
Exec=$bash_bin "$exec_path"
Path=$root
Icon=$icon
Terminal=true
Categories=Education;Development;
StartupNotify=false
EOF
  /bin/chmod u+rwx,go+rx "$path" 2>/dev/null || chmod u+rwx,go+rx "$path" 2>/dev/null || true
  if command -v gio >/dev/null 2>&1; then
    gio set "$path" metadata::trusted true 2>/dev/null || true
  fi
}

_write_linux_desktop_args() {
  local path="$1" name="$2" exec_path="$3" args="$4" icon="$5" root="$6" bash_bin="$7"
  local comment="${8:-Task Studio Launcher}"
  cat >"$path" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$name
Comment=$comment
Exec=$bash_bin "$exec_path" $args
Path=$root
Icon=$icon
Terminal=true
Categories=Education;Development;
StartupNotify=false
EOF
  /bin/chmod u+rwx,go+rx "$path" 2>/dev/null || chmod u+rwx,go+rx "$path" 2>/dev/null || true
  if command -v gio >/dev/null 2>&1; then
    gio set "$path" metadata::trusted true 2>/dev/null || true
  fi
}

_write_macos_command() {
  local path="$1" script="$2" icon="$3" bash_bin="$4"
  local fail_msg blocked close_prompt
  if declare -f ts_t >/dev/null 2>&1; then
    fail_msg="$(ts_t shortcut_fail_exit '%s')"
    fail_msg="${fail_msg//'%s'/\$status}"
    blocked="$(ts_t shortcut_blocked_hint)"
    close_prompt="$(ts_t press_enter_close)"
  else
    fail_msg='Task Studio Launcher failed with exit code $status.'
    blocked='If the script is blocked, run from Terminal:'
    close_prompt='Press Enter to close…'
  fi
  cat >"$path" <<EOF
#!/bin/bash
script="$script"
root="\$(cd "\$(dirname "\$script")/.." && pwd)"
cd "\$root" || exit 1
"$bash_bin" "\$script"
status=\$?
if [[ \$status -ne 0 ]]; then
  echo
  echo "$fail_msg"
  echo "$blocked"
  echo "  bash \"\$script\""
fi
echo
read -r -p "$close_prompt"
exit \$status
EOF
  /bin/chmod u+rwx,go+rx "$path" 2>/dev/null || chmod u+rwx,go+rx "$path" 2>/dev/null || true
  if command -v xattr >/dev/null 2>&1; then
    xattr -d com.apple.quarantine "$path" 2>/dev/null || true
    xattr -d com.apple.quarantine "$script" 2>/dev/null || true
  fi
  _macos_set_icon "$path" "$icon"
}

_write_macos_command_args() {
  local path="$1" script="$2" args="$3" icon="$4" bash_bin="$5"
  local fail_msg close_prompt
  if declare -f ts_t >/dev/null 2>&1; then
    fail_msg="$(ts_t shortcut_fail_exit '%s')"
    fail_msg="${fail_msg//'%s'/\$status}"
    close_prompt="$(ts_t press_enter_close)"
  else
    fail_msg='Task Studio Launcher failed with exit code $status.'
    close_prompt='Press Enter to close…'
  fi
  cat >"$path" <<EOF
#!/bin/bash
script="$script"
root="\$(cd "\$(dirname "\$script")/.." && pwd)"
cd "\$root" || exit 1
"$bash_bin" "\$script" $args
status=\$?
if [[ \$status -ne 0 ]]; then
  echo
  echo "$fail_msg"
fi
echo
read -r -p "$close_prompt"
exit \$status
EOF
  /bin/chmod u+rwx,go+rx "$path" 2>/dev/null || chmod u+rwx,go+rx "$path" 2>/dev/null || true
  if command -v xattr >/dev/null 2>&1; then
    xattr -d com.apple.quarantine "$path" 2>/dev/null || true
  fi
  _macos_set_icon "$path" "$icon"
}

_macos_set_icon() {
  local path="$1" icon="$2"
  if [[ -f "$icon" ]] && command -v osascript >/dev/null 2>&1; then
    osascript <<OSA 2>/dev/null || true
use framework "Foundation"
use framework "AppKit"
set imageData to (current application's NSImage's alloc()'s initWithContentsOfFile:"$icon")
if imageData is not missing value then
  (current application's NSWorkspace's sharedWorkspace()'s setIcon:imageData forFile:"$path" options:0)
end if
OSA
  fi
}
