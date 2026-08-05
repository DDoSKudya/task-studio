#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="deploy/docker-compose.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_CANDIDATE="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=lib/i18n.sh
source "$SCRIPT_DIR/lib/i18n.sh"
# shellcheck source=lib/ui.sh
source "$SCRIPT_DIR/lib/ui.sh"
# shellcheck source=lib/progress.sh
source "$SCRIPT_DIR/lib/progress.sh"
# shellcheck source=lib/profiles.sh
source "$SCRIPT_DIR/lib/profiles.sh"
# shellcheck source=lib/health.sh
source "$SCRIPT_DIR/lib/health.sh"
# shellcheck source=lib/desktop.sh
source "$SCRIPT_DIR/lib/desktop.sh"
# shellcheck source=lib/ops.sh
source "$SCRIPT_DIR/lib/ops.sh"

studio_usage() {
  cat <<EOF
$(ui_c "$TS_VIOLET")$(ts_t usage_header)$(ui_c "$TS_RESET")

$(ts_t usage_body)
EOF
}

studio_menu_items() {
  local state update_status
  state="$(ops_stack_state)"
  ops_update_check >/dev/null 2>&1 || true
  update_status="${TS_UPDATE_STATUS:-error}"
  STUDIO_MENU_ITEMS=()
  case "$state" in
    missing)
      STUDIO_MENU_ITEMS+=(
        "install|$(ts_t menu_install)"
      )
      ;;
    stopped)
      STUDIO_MENU_ITEMS+=(
        "start|$(ts_t menu_start)"
        "install|$(ts_t menu_install_repair)"
        "uninstall|$(ts_t menu_uninstall)"
      )
      ;;
    running)
      STUDIO_MENU_ITEMS+=(
        "open|$(ts_t menu_open)"
        "heal|$(ts_t menu_heal)"
        "restart|$(ts_t menu_restart)"
        "install|$(ts_t menu_install_repair)"
        "stop|$(ts_t menu_stop)"
        "uninstall|$(ts_t menu_uninstall)"
      )
      ;;
  esac
  if [[ "${TS_UPDATE_AVAILABLE:-0}" -eq 1 ]]; then
    STUDIO_MENU_ITEMS+=(
      "update|$(ts_t menu_update)"
    )
  elif [[ "$update_status" != "unsupported" ]]; then
    STUDIO_MENU_ITEMS+=(
      "update|$(ts_t menu_check_updates)"
    )
  fi
  STUDIO_MENU_ITEMS+=(
    "help|$(ts_t menu_help)"
    "quit|$(ts_t menu_quit)"
  )
  STUDIO_MENU_STATE="$state"
  STUDIO_UPDATE_STATUS="$update_status"
}

studio_run_action() {
  local pick="$1"
  case "$pick" in
    start)
      ui_run_progress "$(ts_t title_start)" ops_start || true
      ;;
    heal)
      ui_run_progress "$(ts_t title_start)" ops_start || true
      ;;
    open)
      ops_open || true
      ;;
    stop)
      ui_run_progress "$(ts_t title_stop)" ops_stop || true
      ;;
    restart)
      ui_run_progress "$(ts_t title_restart)" ops_restart || true
      ;;
    install)
      ui_run_progress "$(ops_install_title)" ops_install || true
      ;;
    update)
      TS_UPDATE_REEXEC=0
      ui_run_progress "$(ts_t title_update)" ops_update_apply || true
      if [[ "${TS_UPDATE_REEXEC:-0}" == "1" ]]; then
        ui_session_end
        exec bash "$SCRIPT_DIR/studio.sh"
      fi
      ;;
    uninstall)
      if ops_uninstall_confirm; then
        ui_run_progress "$(ts_t title_uninstall)" ops_uninstall_run || true
        if ops_uninstall_should_exit; then
          return 1
        fi
      else
        [[ -n "${TS_UNINSTALL_EXIT_FILE:-}" ]] && rm -f "$TS_UNINSTALL_EXIT_FILE" 2>/dev/null || true
      fi
      ;;
    help)
      ui_show_text "$(ts_t help_title)" \
        "$(ts_t help_line_menu)" \
        "$(ts_t help_line_install)" \
        "$(ts_t help_line_start)" \
        "$(ts_t help_line_open)" \
        "$(ts_t help_line_stop)" \
        "$(ts_t help_line_restart)" \
        "$(ts_t help_line_update)" \
        "$(ts_t help_line_uninstall)" \
        "" \
        "$(ts_t help_update_note1)" \
        "$(ts_t help_update_note2)" \
        "$(ts_t help_update_note3)"
      ;;
    quit)
      return 1
      ;;
    *)
      ui_die "$(ts_t unknown_choice "$pick")"
      ;;
  esac
  return 0
}

studio_menu() {
  local pick prompt
  ui_session_start
  # shellcheck disable=SC2064
  trap 'ui_session_end' EXIT

  while true; do
    if [[ -f "$ROOT_CANDIDATE/$COMPOSE_FILE" ]]; then
      cd "$ROOT_CANDIDATE"
    fi
    studio_menu_items
    case "${STUDIO_MENU_STATE:-unknown}" in
      missing) prompt="$(ts_t prompt_missing)" ;;
      stopped) prompt="$(ts_t prompt_stopped)" ;;
      running) prompt="$(ts_t prompt_running)" ;;
      *) prompt="$(ts_t prompt_default)" ;;
    esac
    if [[ "${TS_UPDATE_AVAILABLE:-0}" -eq 1 ]]; then
      prompt="$(ts_t prompt_update)"
    fi
    pick="$(ui_choose "$prompt" "${STUDIO_MENU_ITEMS[@]}")" || {
      trap - EXIT
      ui_session_end
      return 0
    }
    if [[ "$pick" == "quit" ]]; then
      trap - EXIT
      ui_session_end
      return 0
    fi
    studio_run_action "$pick" || true
  done
}

main() {
  if [[ -f "$ROOT_CANDIDATE/$COMPOSE_FILE" ]]; then
    cd "$ROOT_CANDIDATE"
    export TS_ROOT="$ROOT_CANDIDATE"
  fi

  local cmd="${1:-}"
  case "$cmd" in
    help|-h|--help)
      studio_usage
      return 0
      ;;
    open)
      shift || true
      ops_open "$@"
      return 0
      ;;
    ""|install|start|heal|stop|restart|uninstall|remove|update|menu)
      ;;
    *)
      ui_err "$(ts_t unknown_command "$cmd")"
      studio_usage
      exit 1
      ;;
  esac

  ops_need_docker

  if [[ -z "$cmd" ]]; then
    if [[ -t 0 ]] || [[ -r /dev/tty ]]; then
      studio_menu
    else
      studio_usage
      exit 1
    fi
    return
  fi
  shift || true
  case "$cmd" in
    install)
      if { [[ -t 2 ]] || [[ -r /dev/tty ]]; } && ui_supports_color; then
        ui_session_start
        trap 'ui_session_end' EXIT
        ui_run_progress "$(ops_install_title)" ops_install "$@" || true
        trap - EXIT
        ui_session_end
      else
        ops_install "$@"
      fi
      ;;
    start|heal)
      if { [[ -t 2 ]] || [[ -r /dev/tty ]]; } && ui_supports_color; then
        ui_session_start
        trap 'ui_session_end' EXIT
        ui_run_progress "$(ts_t title_start)" ops_start "$@" || true
        trap - EXIT
        ui_session_end
      else
        ops_start "$@"
      fi
      ;;
    stop)
      if { [[ -t 2 ]] || [[ -r /dev/tty ]]; } && ui_supports_color; then
        ui_session_start
        trap 'ui_session_end' EXIT
        ui_run_progress "$(ts_t title_stop)" ops_stop "$@" || true
        trap - EXIT
        ui_session_end
      else
        ops_stop "$@"
      fi
      ;;
    restart)
      if { [[ -t 2 ]] || [[ -r /dev/tty ]]; } && ui_supports_color; then
        ui_session_start
        trap 'ui_session_end' EXIT
        ui_run_progress "$(ts_t title_restart)" ops_restart "$@" || true
        trap - EXIT
        ui_session_end
      else
        ops_restart "$@"
      fi
      ;;
    uninstall|remove)
      if { [[ -t 2 ]] || [[ -r /dev/tty ]]; } && ui_supports_color; then
        ui_session_start
        trap 'ui_session_end' EXIT
        if ops_uninstall_confirm "$@"; then
          ui_run_progress "$(ts_t title_uninstall)" ops_uninstall_run || true
          if ops_uninstall_should_exit; then
            trap - EXIT
            ui_session_end
            return 0
          fi
        else
          [[ -n "${TS_UNINSTALL_EXIT_FILE:-}" ]] && rm -f "$TS_UNINSTALL_EXIT_FILE" 2>/dev/null || true
        fi
        trap - EXIT
        ui_session_end
      else
        ops_uninstall "$@"
      fi
      ;;
    update)
      if { [[ -t 2 ]] || [[ -r /dev/tty ]]; } && ui_supports_color; then
        ui_session_start
        trap 'ui_session_end' EXIT
        TS_UPDATE_REEXEC=0
        ui_run_progress "$(ts_t title_update)" ops_update_apply "$@" || true
        trap - EXIT
        ui_session_end
        if [[ "${TS_UPDATE_REEXEC:-0}" == "1" ]]; then
          exec bash "$SCRIPT_DIR/studio.sh"
        fi
      else
        ops_update_apply "$@"
      fi
      ;;
    help|-h|--help) studio_usage ;;
    menu) studio_menu ;;
    *)
      ui_err "$(ts_t unknown_command "$cmd")"
      studio_usage
      exit 1
      ;;
  esac
}

main "$@"
