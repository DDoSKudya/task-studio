#!/usr/bin/env bash

TS_HTTP_PORT_CANDIDATES=(80 8080 18080 8888 9080 3000 8000)

ts_http_port_from_env_file() {
  if [[ ! -f .env ]]; then
    return 0
  fi
  grep -E '^TASK_STUDIO_HTTP_PORT=' .env 2>/dev/null | head -1 | cut -d= -f2- | sed "s/[\"'[:space:]]//g" || true
}

ts_preferred_http_port() {
  if [[ "${TASK_STUDIO_HTTP_PORT:-}" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$TASK_STUDIO_HTTP_PORT"
    return 0
  fi
  local from_file
  from_file="$(ts_http_port_from_env_file)"
  if [[ "$from_file" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "$from_file"
    return 0
  fi
  printf '80\n'
}

ts_format_ui_url() {
  local port="${1:-80}"
  if [[ "$port" == "80" ]]; then
    printf 'http://localhost\n'
  else
    printf 'http://localhost:%s\n' "$port"
  fi
}

ts_format_ui_probe_url() {
  local port="${1:-80}"
  if [[ "$port" == "80" ]]; then
    printf 'http://127.0.0.1/api/health\n'
  else
    printf 'http://127.0.0.1:%s/api/health\n' "$port"
  fi
}

ts_loopback_port_busy() {
  local port="$1"
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$port" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.25)
try:
    s.connect(("127.0.0.1", port))
except OSError:
    sys.exit(1)
else:
    s.close()
    sys.exit(0)
PY
    return $?
  fi
  if command -v nc >/dev/null 2>&1; then
    nc -z -w 1 127.0.0.1 "$port" >/dev/null 2>&1
    return $?
  fi
  return 1
}

ts_ui_fingerprint_ok() {
  local url="${1:-$APP_UI_PROBE_URL}"
  local body headers
  headers="$(mktemp 2>/dev/null || echo /tmp/ts-headers.$$)"
  body="$(curl -fsS -D "$headers" -o - --max-time 3 "$url" 2>/dev/null || true)"
  if [[ -z "$body" ]] && [[ ! -s "$headers" ]]; then
    rm -f "$headers"
    return 1
  fi
  if grep -qiE '^X-Task-Studio:[[:space:]]*1' "$headers" 2>/dev/null; then
    rm -f "$headers"
    return 0
  fi
  rm -f "$headers"
  if printf '%s' "$body" | grep -qE '"status"[[:space:]]*:[[:space:]]*"(ok|degraded)"'; then
    return 0
  fi
  return 1
}

ts_sync_ui_endpoint_vars() {
  local port="$1"
  local ui probe
  ui="$(ts_format_ui_url "$port")"
  probe="$(ts_format_ui_probe_url "$port")"
  export TASK_STUDIO_HTTP_PORT="$port"
  case "${TASK_STUDIO_UI_URL:-}" in
    ''|http://localhost|http://localhost:*|http://127.0.0.1|http://127.0.0.1:*|https://localhost|https://localhost:*|https://127.0.0.1|https://127.0.0.1:*)
      export TASK_STUDIO_UI_URL="$ui"
      ;;
  esac
  export TASK_STUDIO_UI_PROBE_URL="$probe"
  APP_UI_URL="$TASK_STUDIO_UI_URL"
  APP_UI_PROBE_URL="$probe"
}

resolve_ts_http_port() {
  local preferred existing port
  preferred="$(ts_preferred_http_port)"
  existing="$(ts_http_port_from_env_file)"
  if [[ "$existing" =~ ^[0-9]+$ ]]; then

    if ts_ui_fingerprint_ok "$(ts_format_ui_probe_url "$existing")"; then
      ts_sync_ui_endpoint_vars "$existing"
      printf '%s\n' "$existing"
      return 0
    fi

    if ! ts_loopback_port_busy "$existing"; then
      ts_sync_ui_endpoint_vars "$existing"
      printf '%s\n' "$existing"
      return 0
    fi

  fi

  local -a ordered=()
  local seen="|"
  for port in "$preferred" "${TS_HTTP_PORT_CANDIDATES[@]}"; do
    [[ "$port" =~ ^[0-9]+$ ]] || continue
    [[ "$seen" == *"|$port|"* ]] && continue
    seen+="$port|"
    ordered+=("$port")
  done

  for port in "${ordered[@]}"; do
    if ts_ui_fingerprint_ok "$(ts_format_ui_probe_url "$port")"; then
      ts_sync_ui_endpoint_vars "$port"
      printf '%s\n' "$port"
      return 0
    fi
    if ts_loopback_port_busy "$port"; then
      continue
    fi
    ts_sync_ui_endpoint_vars "$port"
    printf '%s\n' "$port"
    return 0
  done
  echo "No free HTTP port for Task Studio UI (tried: ${ordered[*]}). Set TASK_STUDIO_HTTP_PORT." >&2
  return 1
}

APP_UI_URL="${TASK_STUDIO_UI_URL:-http://localhost}"
APP_UI_PROBE_URL="${TASK_STUDIO_UI_PROBE_URL:-http://127.0.0.1/api/health}"

wait_http_ok() {
  local url="${1:-$APP_UI_PROBE_URL}"
  local tries="${2:-60}"
  local sleep_s="${3:-3}"
  local i
  for ((i = 1; i <= tries; i++)); do
    if ts_ui_fingerprint_ok "$url"; then
      return 0
    fi
    sleep "$sleep_s"
  done
  return 1
}

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

ts_ui_failure_hint() {
  local url="${1:-$APP_UI_URL}"
  local port
  port="$(ts_preferred_http_port)"
  if ts_loopback_port_busy "$port" && ! ts_ui_fingerprint_ok "$APP_UI_PROBE_URL"; then
    if declare -f ts_t >/dev/null 2>&1; then
      ts_t err_ui_port_conflict "$port" "$url"
    else
      printf 'Port %s on loopback is occupied by another program. UI: %s\n' "$port" "$url"
    fi
    return 0
  fi
  if declare -f ts_t >/dev/null 2>&1; then
    ts_t err_ui "$url"
  else
    printf 'UI is not responding at %s\n' "$url"
  fi
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
