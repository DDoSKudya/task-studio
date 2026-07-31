# Shared health / browser helpers for install + start (bash).
# Source after profiles.sh; expects cwd = repo root.

APP_UI_URL="${TASK_STUDIO_UI_URL:-http://localhost}"
APP_UI_PROBE_URL="${TASK_STUDIO_UI_PROBE_URL:-http://127.0.0.1}"

wait_http_ok() {
  local url="${1:-$APP_UI_PROBE_URL}"
  local tries="${2:-60}"
  local sleep_s="${3:-3}"
  local i
  for ((i = 1; i <= tries; i++)); do
    if curl -fsS -o /dev/null --max-time 3 "$url" 2>/dev/null; then
      return 0
    fi
    sleep "$sleep_s"
  done
  return 1
}

# Best-effort: compose reports the edge proxy as running/healthy.
stack_edge_ok() {
  local compose="${COMPOSE_FILE:-deploy/docker-compose.yml}"
  local pname="${COMPOSE_PROJECT_NAME:-task-studio}"
  local line
  if [[ ! -f .env ]]; then
    return 0
  fi
  if [[ -z "${COMPOSE_PROJECT_NAME:-}" ]] && grep -qE '^COMPOSE_PROJECT_NAME=' .env 2>/dev/null; then
    pname="$(grep -E '^COMPOSE_PROJECT_NAME=' .env | head -1 | cut -d= -f2- | sed "s/[\"'[:space:]]//g")"
    pname="${pname:-task-studio}"
  fi
  line="$(
    docker compose -p "$pname" -f "$compose" --env-file .env --profile full ps --format '{{.Service}} {{.State}} {{.Health}}' 2>/dev/null \
      | awk '$1 == "nginx" { print; exit }'
  )" || true
  if [[ -z "$line" ]]; then
    return 0
  fi
  case "$line" in
    *running*|*healthy*) return 0 ;;
    *) return 1 ;;
  esac
}

wait_app_ready() {
  local tries="${1:-60}"
  local sleep_s="${2:-3}"
  local i
  for ((i = 1; i <= tries; i++)); do
    if wait_http_ok "$APP_UI_PROBE_URL" 1 0 && stack_edge_ok; then
      return 0
    fi
    sleep "$sleep_s"
  done
  return 1
}

open_app_ui() {
  local url="${1:-$APP_UI_URL}"
  case "$(uname -s)" in
    Darwin)
      open "$url" >/dev/null 2>&1 || true
      ;;
    *)
      if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$url" >/dev/null 2>&1 || true
      elif command -v sensible-browser >/dev/null 2>&1; then
        sensible-browser "$url" >/dev/null 2>&1 || true
      elif command -v gio >/dev/null 2>&1; then
        gio open "$url" >/dev/null 2>&1 || true
      else
        if declare -f ts_t >/dev/null 2>&1; then
          printf '%s\n' "$(ts_t info_open_manual "$url")"
        else
          printf 'Open in browser: %s\n' "$url"
        fi
      fi
      ;;
  esac
}
