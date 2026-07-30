# Ops used by scripts/studio.sh (source after ui/profiles/health/desktop).
# Expects: COMPOSE_FILE, TS_ROOT / ROOT, cwd may change inside functions.

REPO_SSH="${TASK_STUDIO_REPO_SSH:-git@github.com:DDoSKudya/task-studio.git}"
REPO_HTTPS="${TASK_STUDIO_REPO_HTTPS:-https://github.com/DDoSKudya/task-studio.git}"
REPO_BRANCH="${TASK_STUDIO_BRANCH:-develop}"
INSTALL_DIR="${TASK_STUDIO_DIR:-$HOME/task-studio}"
MIN_RAM_GB="${TASK_STUDIO_MIN_RAM_GB:-8}"
OLLAMA_MODEL_DEFAULT="${OLLAMA_MODEL:-qwen2.5:3b}"

ops_need_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    ui_die "$(ts_t err_docker_missing)"
  fi
  local info_err
  if ! info_err="$(docker info 2>&1 >/dev/null)"; then
    if [[ -n "${info_err//[[:space:]]/}" ]]; then
      ui_die "$(ts_t err_docker_unusable "$info_err")"
    fi
    ui_die "$(ts_t err_docker_stopped)"
  fi
  if ! docker compose version >/dev/null 2>&1; then
    ui_die "$(ts_t err_compose_missing)"
  fi
}

ops_detect_ram_gb() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    local bytes
    bytes="$(sysctl -n hw.memsize 2>/dev/null || echo 0)"
    echo $((bytes / 1024 / 1024 / 1024))
    return
  fi
  if [[ -r /proc/meminfo ]]; then
    awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo
    return
  fi
  echo 0
}

ops_ensure_repo() {
  if [[ -f "$COMPOSE_FILE" && -f ".env.example" ]]; then
    ROOT="$(pwd -P)"
    return
  fi
  if [[ -f "$INSTALL_DIR/$COMPOSE_FILE" ]]; then
    cd "$INSTALL_DIR"
    ROOT="$(pwd -P)"
    return
  fi
  ui_info "$(ts_t info_clone "$INSTALL_DIR")"
  command -v git >/dev/null 2>&1 || ui_die "$(ts_t err_git)"
  mkdir -p "$(dirname "$INSTALL_DIR")"
  if git clone --branch "$REPO_BRANCH" --depth 1 "$REPO_HTTPS" "$INSTALL_DIR" 2>/dev/null; then
    :
  else
    git clone --branch "$REPO_BRANCH" --depth 1 "$REPO_SSH" "$INSTALL_DIR"
  fi
  cd "$INSTALL_DIR"
  ROOT="$(pwd -P)"
}

ops_ensure_env() {
  if [[ ! -f .env ]]; then
    cp .env.example .env
    ui_info "$(ts_t info_env_created)"
  fi

  local key="" jwt="" gid cur

  if command -v python3 >/dev/null 2>&1; then
    key="$(python3 - <<'PY'
import base64, os, re, pathlib
text = pathlib.Path(".env").read_text(encoding="utf-8")
m = re.search(r"^SECRETS_MASTER_KEY=(.*)$", text, re.M)
raw = (m.group(1).strip().strip('"').strip("'") if m else "")
ok = False
if raw and "change-me" not in raw.lower():
    try:
        ok = len(base64.b64decode(raw, validate=True)) == 32
    except Exception:
        ok = False
if not ok:
    print(base64.b64encode(os.urandom(32)).decode("ascii"))
PY
)"
    jwt="$(python3 - <<'PY'
import re, pathlib, secrets
text = pathlib.Path(".env").read_text(encoding="utf-8")
m = re.search(r"^JWT_SECRET=(.*)$", text, re.M)
raw = (m.group(1).strip().strip('"').strip("'") if m else "")
if not raw or "change-me" in raw.lower() or len(raw) < 16:
    print(secrets.token_urlsafe(48))
PY
)"
  else
    command -v openssl >/dev/null 2>&1 || ui_die "$(ts_t err_openssl)"
    cur="$(grep -E '^SECRETS_MASTER_KEY=' .env | head -1 | cut -d= -f2- || true)"
    if [[ -z "$cur" || "$cur" == *change-me* ]]; then
      key="$(openssl rand -base64 32 | tr -d '\n')"
    fi
    cur="$(grep -E '^JWT_SECRET=' .env | head -1 | cut -d= -f2- || true)"
    if [[ -z "$cur" || "$cur" == *change-me* || ${#cur} -lt 16 ]]; then
      jwt="$(openssl rand -base64 48 | tr -d '\n')"
    fi
  fi

  if [[ -n "${key:-}" ]]; then
    if grep -q '^SECRETS_MASTER_KEY=' .env; then
      sed -i.bak "s|^SECRETS_MASTER_KEY=.*|SECRETS_MASTER_KEY=$key|" .env
    else
      printf '\nSECRETS_MASTER_KEY=%s\n' "$key" >> .env
    fi
    rm -f .env.bak
    ui_info "$(ts_t info_secrets_key)"
  fi

  if [[ -n "${jwt:-}" ]]; then
    if grep -q '^JWT_SECRET=' .env; then
      sed -i.bak "s|^JWT_SECRET=.*|JWT_SECRET=$jwt|" .env
    else
      printf '\nJWT_SECRET=%s\n' "$jwt" >> .env
    fi
    rm -f .env.bak
    ui_info "$(ts_t info_jwt)"
  fi

  if grep -q '^OLLAMA_MODEL=' .env; then
    if grep -qE '^OLLAMA_MODEL=\s*$|^OLLAMA_MODEL=llama3\.2\s*$' .env; then
      sed -i.bak "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$OLLAMA_MODEL_DEFAULT|" .env
      rm -f .env.bak
    fi
  else
    printf '\nOLLAMA_MODEL=%s\n' "$OLLAMA_MODEL_DEFAULT" >> .env
  fi

  if [[ "$(uname -s)" == "Linux" ]] && command -v getent >/dev/null 2>&1; then
    gid="$(getent group docker 2>/dev/null | cut -d: -f3 || true)"
    if [[ -n "${gid:-}" ]]; then
      if grep -q '^DOCKER_GID=' .env; then
        sed -i.bak "s|^DOCKER_GID=.*|DOCKER_GID=$gid|" .env
      else
        printf '\nDOCKER_GID=%s\n' "$gid" >> .env
      fi
      rm -f .env.bak
    fi
  fi
}

ops_prepare_dirs() {
  mkdir -p \
    data/postgres data/redis data/rabbitmq data/packs \
    data/meilisearch data/clickhouse data/minio data/ollama \
    data/grafana data/prometheus data/piston/packages
  chmod -R a+rwX data/packs 2>/dev/null || true
}

ops_compose() {
  docker compose -f "$COMPOSE_FILE" --env-file .env "$@"
}

# Soft root lookup (no die). Sets ROOT and cd when found.
ops_find_root_quiet() {
  if [[ -f "$COMPOSE_FILE" ]]; then
    ROOT="$(pwd -P)"
    return 0
  fi
  if [[ -f "${INSTALL_DIR:-$HOME/task-studio}/$COMPOSE_FILE" ]]; then
    cd "${INSTALL_DIR:-$HOME/task-studio}"
    ROOT="$(pwd -P)"
    return 0
  fi
  if [[ -f "$HOME/task-studio/$COMPOSE_FILE" ]]; then
    cd "$HOME/task-studio"
    ROOT="$(pwd -P)"
    return 0
  fi
  return 1
}

# Count running containers for this compose project (0 if unknown).
ops_running_count() {
  local n
  if [[ ! -f .env ]] || [[ ! -f "$COMPOSE_FILE" ]]; then
    printf '0\n'
    return
  fi
  if ! command -v docker >/dev/null 2>&1; then
    printf '0\n'
    return
  fi
  n="$(
    docker compose -f "$COMPOSE_FILE" --env-file .env \
      --profile full --profile editor --profile host-metrics \
      ps --format '{{.State}}' 2>/dev/null \
      | grep -ciE 'running|healthy' || true
  )"
  [[ "$n" =~ ^[0-9]+$ ]] || n=0
  printf '%s\n' "$n"
}

# One of: missing | stopped | running
ops_stack_state() {
  local here
  here="$(pwd -P)"
  if ! ops_find_root_quiet; then
    cd "$here" 2>/dev/null || true
    printf 'missing\n'
    return
  fi
  if [[ ! -f .env ]]; then
    cd "$here" 2>/dev/null || true
    printf 'missing\n'
    return
  fi
  local n
  n="$(ops_running_count)"
  if [[ "$n" -gt 0 ]]; then
    printf 'running\n'
  else
    printf 'stopped\n'
  fi
}

ops_stack_state_label() {
  case "$(ops_stack_state)" in
    missing) printf 'not installed' ;;
    stopped) printf 'stopped' ;;
    running) printf 'running' ;;
    *) printf 'unknown' ;;
  esac
}

# Stop stack without removing volumes (used before uninstall / restart).
ops_ensure_stopped() {
  [[ -f "$COMPOSE_FILE" ]] || return 0
  if [[ -f .env ]]; then
    docker compose -f "$COMPOSE_FILE" --env-file .env \
      --profile full --profile editor --profile host-metrics \
      down --remove-orphans || true
  else
    docker compose -f "$COMPOSE_FILE" \
      --profile full --profile editor --profile host-metrics \
      down --remove-orphans || true
  fi
  local n left=15
  while ((left > 0)); do
    n="$(ops_running_count)"
    ((n == 0)) && return 0
    sleep 1
    left=$((left - 1))
  done
  n="$(ops_running_count)"
  ((n == 0)) || return 1
  return 0
}

ops_pull_ollama() {
  local model
  model="$(grep -E '^OLLAMA_MODEL=' .env | head -1 | cut -d= -f2- | tr -d '[:space:]')"
  model="${model:-$OLLAMA_MODEL_DEFAULT}"
  ui_info "$(ts_t info_pull_model "$model")"
  ops_compose --profile full exec -T ollama ollama pull "$model" \
    || ui_warn "$(ts_t warn_model_pull "$COMPOSE_FILE" "$model")"
}

ops_resolve_root() {
  if ROOT="$(resolve_repo_root)"; then
    cd "$ROOT"
    return 0
  fi
  if [[ -f "$COMPOSE_FILE" ]]; then
    ROOT="$(pwd -P)"
    return 0
  fi
  if [[ -f "$HOME/task-studio/$COMPOSE_FILE" ]]; then
    cd "$HOME/task-studio"
    ROOT="$(pwd -P)"
    return 0
  fi
  return 1
}

ops_install() {
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1

  ts_prog_begin "$(ts_t title_install)"
  ts_prog_plan \
    "prepare|$(ts_t stage_prepare)|40" \
    "build|$(ts_t stage_build)|600" \
    "start|$(ts_t stage_start)|50" \
    "health|$(ts_t stage_health)|90" \
    "model|$(ts_t stage_model)|240" \
    "finish|$(ts_t stage_finish)|25"

  ts_prog_enter prepare "$(ts_t status_check_docker)"
  ops_need_docker

  local ram
  ram="$(ops_detect_ram_gb)"
  if [[ "$ram" -gt 0 && "$ram" -lt "$MIN_RAM_GB" ]]; then
    ui_die "$(ts_t err_ram "$ram" "$MIN_RAM_GB")"
  fi
  if [[ "$ram" -gt 0 && "$ram" -lt 16 ]]; then
    export ORCHESTRATOR_MODE="${ORCHESTRATOR_MODE:-power_saving}"
    ts_prog_status "$(ts_t status_ram_power "$ram")"
  fi

  ts_prog_status "$(ts_t status_ensure_repo)"
  ops_ensure_repo
  cd "$ROOT"
  export TS_ROOT="$ROOT"
  ops_ensure_env
  ops_prepare_dirs

  local profile_args
  profile_args="$(profiles_args | tr '\n' ' ')"
  if ! can_use_host_metrics; then
    ts_prog_status "$(ts_t status_skip_metrics)"
  fi

  ts_prog_enter build "$(ts_t status_build_slow)"
  # shellcheck disable=SC2086
  if ! ops_compose $profile_args build; then
    ui_die "$(ts_t err_build)"
  fi

  ts_prog_enter start "$(ts_t status_starting_containers)"
  # shellcheck disable=SC2086
  if ! ops_compose $profile_args up -d --remove-orphans; then
    ui_die "$(ts_t err_up)"
  fi

  ts_prog_enter health "$(ts_t status_waiting_ui "$APP_UI_URL")"
  if wait_app_ready 90 5; then
    ts_prog_status "$(ts_t status_ui_ok)"
    open_app_ui "$APP_UI_URL" || true
  else
    ui_die "$(ts_t err_ui "$APP_UI_URL")"
  fi

  ts_prog_enter model "$(ts_t status_pull_model)"
  ops_pull_ollama

  ts_prog_enter finish "$(ts_t status_shortcuts)"
  ensure_script_permissions "$ROOT"
  create_desktop_shortcuts "$ROOT" || ts_prog_status "$(ts_t status_shortcuts_skip)"

  ts_prog_done
  ui_log "$(ts_t info_dir "$ROOT")"
  ui_log "$(ts_t info_ui "$APP_UI_URL")"
  ui_log "$(ts_t info_console)"
}

ops_open() {
  ops_resolve_root || ui_die "$(ts_t err_not_installed)"
  export TS_ROOT="$ROOT"
  if ! wait_http_ok "$APP_UI_PROBE_URL" 1 0 || ! stack_edge_ok; then
    ui_warn "$(ts_t warn_ui_unreachable "$APP_UI_URL")"
  fi
  open_app_ui "$APP_UI_URL" || true
  ui_info "$(ts_t info_opened_ui "$APP_UI_URL")"
}

ops_start() {
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1

  ts_prog_begin "$(ts_t title_start)"
  ts_prog_plan \
    "prepare|$(ts_t stage_prepare)|20" \
    "start|$(ts_t stage_start)|40" \
    "health|$(ts_t stage_health)|60"

  ts_prog_enter prepare "$(ts_t status_locate)"
  ops_resolve_root || ui_die "$(ts_t err_not_installed)"
  export TS_ROOT="$ROOT"
  ops_need_docker

  if [[ -f .env ]] && grep -qE '^ORCHESTRATOR_MODE=' .env; then
    export ORCHESTRATOR_MODE="$(grep -E '^ORCHESTRATOR_MODE=' .env | head -1 | cut -d= -f2- | tr -d '[:space:]')"
  fi

  local profile_args
  profile_args="$(profiles_args | tr '\n' ' ')"
  if ! can_use_host_metrics; then
    ts_prog_status "$(ts_t status_skip_metrics_short)"
  fi

  ts_prog_enter start "$(ts_t status_starting_ts)"
  # shellcheck disable=SC2086
  if ! ops_compose $profile_args up -d --remove-orphans; then
    ui_die "$(ts_t err_up_short)"
  fi

  ts_prog_enter health "$(ts_t status_check_ui "$APP_UI_PROBE_URL")"
  if wait_app_ready 60 3; then
    open_app_ui "$APP_UI_URL" || true
    ts_prog_done
  else
    ui_die "$(ts_t err_ui "$APP_UI_URL")"
  fi
}

ops_stop() {
  ts_prog_begin "$(ts_t title_stop)"
  ts_prog_plan "prepare|$(ts_t stage_prepare)|10" "stop|$(ts_t stage_stop)|30"

  ts_prog_enter prepare "$(ts_t status_locate_short)"
  ops_resolve_root || ui_die "$(ts_t err_compose_missing_file "$COMPOSE_FILE")"
  [[ -f .env ]] || ui_die "$(ts_t err_no_env_stop)"

  ts_prog_enter stop "$(ts_t status_stopping)"
  if ! ops_ensure_stopped; then
    ui_die "$(ts_t err_still_running)"
  fi
  ts_prog_done
}

ops_restart() {
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1

  ts_prog_begin "$(ts_t title_restart)"
  ts_prog_plan \
    "stop|$(ts_t stage_stop)|35" \
    "start|$(ts_t stage_start)|40" \
    "health|$(ts_t stage_health)|60"

  ts_prog_enter stop "$(ts_t status_stopping)"
  ops_resolve_root || ui_die "$(ts_t err_not_installed)"
  export TS_ROOT="$ROOT"
  ops_need_docker
  [[ -f .env ]] || ui_die "$(ts_t err_no_env_install)"
  if ! ops_ensure_stopped; then
    ui_die "$(ts_t err_stop_before_restart)"
  fi

  if [[ -f .env ]] && grep -qE '^ORCHESTRATOR_MODE=' .env; then
    export ORCHESTRATOR_MODE="$(grep -E '^ORCHESTRATOR_MODE=' .env | head -1 | cut -d= -f2- | tr -d '[:space:]')"
  fi
  local profile_args
  profile_args="$(profiles_args | tr '\n' ' ')"

  ts_prog_enter start "$(ts_t status_starting_containers)"
  # shellcheck disable=SC2086
  if ! ops_compose $profile_args up -d --remove-orphans; then
    ui_die "$(ts_t err_up_after_restart)"
  fi

  ts_prog_enter health "$(ts_t status_check_ui "$APP_UI_PROBE_URL")"
  if wait_app_ready 60 3; then
    open_app_ui "$APP_UI_URL" || true
    ts_prog_done
  else
    ui_die "$(ts_t err_ui_after_restart "$APP_UI_URL")"
  fi
}

ops_is_consumer_root() {
  local root="${1:-${ROOT:-}}"
  [[ -n "$root" ]] || return 1
  [[ -f "$root/.studio-consumer" ]] && return 0
  local want
  want="$(cd "$INSTALL_DIR" 2>/dev/null && pwd -P || true)"
  [[ -n "$want" && "$root" == "$want" ]]
}

# Never delete $HOME or /.
ops_safe_purge_root() {
  local root="$1"
  [[ -n "$root" ]] || return 1
  root="$(cd "$root" 2>/dev/null && pwd -P || true)"
  [[ -n "$root" ]] || return 1
  [[ "$root" != "/" ]] || return 1
  [[ "$root" != "$HOME" ]] || return 1
  [[ "$root" != "/home" && "$root" != "/Users" ]] || return 1
  ops_is_consumer_root "$root" || return 1
  return 0
}

# Delete install dir after this process exits (scripts may still be open).
ops_schedule_delete_root() {
  local root="$1"
  root="$(cd "$root" && pwd -P)"
  local parent
  parent="$(dirname "$root")"
  cd "$parent" || ui_die "$(ts_t err_leave_root "$root")"
  # shellcheck disable=SC2016
  nohup bash -c '
    target="$1"
    sleep 2
    i=0
    while [[ "$i" -lt 20 ]]; do
      rm -rf -- "$target" 2>/dev/null && exit 0
      sleep 1
      i=$((i + 1))
    done
    exit 1
  ' _ "$root" >/dev/null 2>&1 &
  disown 2>/dev/null || true
  TS_UNINSTALL_EXIT=1
  ts_prog_status "$(ts_t status_delete_scheduled "$root")"
}

ops_uninstall() {
  local yes=0 purge=0 arg
  TS_UNINSTALL_EXIT=0
  for arg in "$@"; do
    case "$arg" in
      -y|--yes) yes=1 ;;
      --purge) purge=1 ;;
      -h|--help)
        cat <<'EOF'
Usage: bash scripts/studio.sh uninstall [options]

  -y, --yes    Do not ask for confirmation
  --purge      Also delete the install directory (default ~/task-studio)
EOF
        return 0
        ;;
      *) ui_die "$(ts_t err_unknown_opt "$arg")" ;;
    esac
  done
  if [[ "${TASK_STUDIO_UNINSTALL_YES:-}" == "1" ]]; then
    yes=1
  fi

  ops_resolve_root || ui_die "$(ts_t err_install_not_found)"
  export TS_ROOT="$ROOT"

  # Consumer product install: always remove the whole folder (launcher included).
  if ops_is_consumer_root "$ROOT"; then
    purge=1
  fi

  if [[ "$yes" -ne 1 ]]; then
    ui_warn "$(ts_t warn_uninstall)"
    if [[ "$purge" -eq 1 ]]; then
      if ops_is_consumer_root "$ROOT"; then
        ui_warn "$(ts_t warn_purge_launcher "$ROOT")"
      else
        ui_warn "$(ts_t warn_purge "$ROOT")"
      fi
      if ! ui_confirm_yes; then
        ui_info "$(ts_t info_cancelled)"
        return 1
      fi
    else
      if ! ui_confirm "$(ts_t confirm_uninstall)"; then
        ui_info "$(ts_t info_cancelled)"
        return 1
      fi
      if ui_confirm "$(ts_t confirm_purge)"; then
        purge=1
        ui_warn "$(ts_t warn_purge "$ROOT")"
        if ! ui_confirm_yes; then
          ui_info "$(ts_t info_cancelled)"
          return 1
        fi
      fi
    fi
  fi

  ts_prog_begin "$(ts_t title_uninstall)"
  ts_prog_plan \
    "stop|$(ts_t stage_stop)|30" \
    "remove|$(ts_t stage_remove)|40" \
    "files|$(ts_t stage_files)|20" \
    "finish|$(ts_t stage_finish)|10"

  ops_need_docker

  ts_prog_enter stop "$(ts_t status_ensure_stopped)"
  if ! ops_ensure_stopped; then
    ui_die "$(ts_t err_uninstall_running)"
  fi

  ts_prog_enter remove "$(ts_t status_remove_vol)"
  if [[ -f .env ]]; then
    docker compose -f "$COMPOSE_FILE" --env-file .env \
      --profile full --profile editor --profile host-metrics \
      down -v --rmi local --remove-orphans || true
  else
    docker compose -f "$COMPOSE_FILE" \
      --profile full --profile editor --profile host-metrics \
      down -v --rmi local --remove-orphans || true
  fi

  ts_prog_enter files "$(ts_t status_remove_files)"
  remove_desktop_shortcuts || true

  ts_prog_enter finish "$(ts_t status_cleanup)"
  if [[ "$purge" -eq 1 ]]; then
    if ops_safe_purge_root "$ROOT"; then
      # Leave data/.env in place — the deferred process removes the whole tree.
      ops_schedule_delete_root "$ROOT"
    else
      # Dev tree or unsafe path: wipe local runtime files only.
      [[ -d data ]] && rm -rf data && ts_prog_status "$(ts_t status_removed_data)"
      [[ -f .env ]] && rm -f .env && ts_prog_status "$(ts_t status_removed_env)"
      ts_prog_status "$(ts_t status_purge_skip "${TASK_STUDIO_DIR:-$HOME/task-studio}")"
    fi
  else
    [[ -d data ]] && rm -rf data && ts_prog_status "$(ts_t status_removed_data)"
    [[ -f .env ]] && rm -f .env && ts_prog_status "$(ts_t status_removed_env)"
    ts_prog_status "$(ts_t status_repo_kept)"
  fi
  ts_prog_done
}

# --- Self-update (HTTP version + archive, no git) ----------------------------

TS_UPDATE_TTL_SEC="${TASK_STUDIO_UPDATE_TTL_SEC:-3600}"
TS_UPDATE_AVAILABLE=0
TS_UPDATE_SUMMARY=""
TS_UPDATE_STATUS=""
TS_UPDATE_REMOTE_VERSION=""
TS_UPDATE_LOCAL_VERSION=""
TS_UPDATE_REMOTE_ARCHIVE=""

ops_update_version_url() {
  local branch="${TASK_STUDIO_BRANCH:-$REPO_BRANCH}"
  if [[ -n "${TASK_STUDIO_VERSION_URL:-}" ]]; then
    printf '%s\n' "$TASK_STUDIO_VERSION_URL"
    return
  fi
  printf 'https://raw.githubusercontent.com/DDoSKudya/task-studio/%s/studio-version.json\n' "$branch"
}

ops_update_stamp_path() {
  local root="${1:-${ROOT:-.}}"
  printf '%s\n' "$root/.studio-update-check"
}

ops_update_state_path() {
  local root="${1:-${ROOT:-.}}"
  printf '%s\n' "$root/.studio-state.json"
}

ops_update_should_fetch() {
  local force="${1:-0}" stamp root now last
  root="$(pwd -P)"
  stamp="$(ops_update_stamp_path "$root")"
  [[ "$force" == "1" || "$force" == "force" ]] && return 0
  [[ -f "$stamp" ]] || return 0
  now="$(date +%s)"
  last="$(tr -d '[:space:]' <"$stamp" 2>/dev/null || echo 0)"
  [[ "$last" =~ ^[0-9]+$ ]] || return 0
  ((now - last >= TS_UPDATE_TTL_SEC))
}

ops_update_touch_stamp() {
  local root stamp
  root="$(pwd -P)"
  stamp="$(ops_update_stamp_path "$root")"
  date +%s >"$stamp" 2>/dev/null || true
}

ops_json_get() {
  # usage: ops_json_get <file-or-> <key>
  local src="$1" key="$2"
  if command -v python3 >/dev/null 2>&1; then
    if [[ "$src" == "-" ]]; then
      python3 -c 'import json,sys; d=json.load(sys.stdin); v=d.get(sys.argv[1],""); print(v if v is not None else "")' "$key"
    else
      python3 -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8")); v=d.get(sys.argv[2],""); print(v if v is not None else "")' "$src" "$key"
    fi
    return
  fi
  # Fallback: fragile single-line extract
  if [[ "$src" == "-" ]]; then
    src="$(cat)"
    printf '%s' "$src" | sed -n "s/.*\"${key}\"[[:space:]]*:[[:space:]]*\"\\([^\"]*\\)\".*/\\1/p" | head -1
  else
    sed -n "s/.*\"${key}\"[[:space:]]*:[[:space:]]*\"\\([^\"]*\\)\".*/\\1/p" "$src" | head -1
  fi
}

ops_local_version() {
  local state manifest
  state="$(ops_update_state_path)"
  manifest="studio-version.json"
  if [[ -f "$state" ]]; then
    ops_json_get "$state" version
    return
  fi
  if [[ -f "$manifest" ]]; then
    ops_json_get "$manifest" version
    return
  fi
  printf '0\n'
}

ops_write_state() {
  local version="$1" content_sha="${2:-}"
  local state
  state="$(ops_update_state_path)"
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json,sys; json.dump({"version":sys.argv[1],"content_sha256":sys.argv[2]}, open(sys.argv[3],"w",encoding="utf-8"), indent=2); open(sys.argv[3],"a",encoding="utf-8").write("\n")' \
      "$version" "$content_sha" "$state"
  else
    printf '{\n  "version": "%s",\n  "content_sha256": "%s"\n}\n' "$version" "$content_sha" >"$state"
  fi
}

ops_mark_consumer() {
  local root="${1:-$(pwd -P)}"
  : >"$root/.studio-consumer"
}

# True for ~/task-studio (or TASK_STUDIO_DIR) / marked consumer installs.
ops_is_updatable_install() {
  local root want
  root="$(pwd -P)"
  [[ -f "$root/.studio-consumer" ]] && return 0
  [[ "${TASK_STUDIO_ALLOW_SELF_UPDATE:-0}" == "1" ]] && return 0
  want="$(cd "$INSTALL_DIR" 2>/dev/null && pwd -P || true)"
  [[ -n "$want" && "$root" == "$want" ]]
}

# Content fingerprint of app files. Never includes user data (.env, data/, …).
ops_content_sha256() {
  local root="$1"
  (
    cd "$root" || exit 1
    # shellcheck disable=SC2016
    find . -type f \
      ! -path './data/*' \
      ! -path './.git/*' \
      ! -path './.cursor/*' \
      ! -path './.plan/*' \
      ! -path './.venv/*' \
      ! -path './node_modules/*' \
      ! -path '*/node_modules/*' \
      ! -path '*/__pycache__/*' \
      ! -path './scripts/.bin/*' \
      ! -name '.env' \
      ! -name '.env.local' \
      ! -name '.studio-update-check' \
      ! -name '.studio-state.json' \
      ! -name '.studio-consumer' \
      ! -name 'compose.override.yml' \
      ! -name 'docker-compose.override.yml' \
      | LC_ALL=C sort \
      | while IFS= read -r f; do
          # skip empty
          [[ -n "$f" ]] || continue
          if command -v sha256sum >/dev/null 2>&1; then
            printf '%s  %s\n' "$(sha256sum "$f" | awk '{print $1}')" "$f"
          else
            printf '%s  %s\n' "$(shasum -a 256 "$f" | awk '{print $1}')" "$f"
          fi
        done \
      | if command -v sha256sum >/dev/null 2>&1; then sha256sum; else shasum -a 256; fi \
      | awk '{print $1}'
  )
}

ops_update_rsync_excludes() {
  # Args for rsync --exclude (leading / = relative to transfer root)
  printf '%s\n' \
    '/data/' \
    '/.env' \
    '/.env.local' \
    '/.studio-update-check' \
    '/.studio-state.json' \
    '/.studio-consumer' \
    '/.git/' \
    '/compose.override.yml' \
    '/docker-compose.override.yml'
}

ops_sync_payload() {
  local src="$1" dst="$2"
  command -v rsync >/dev/null 2>&1 || ui_die "$(ts_t err_rsync)"
  local args=()
  local ex
  while IFS= read -r ex; do
    [[ -n "$ex" ]] || continue
    args+=(--exclude="$ex")
  done < <(ops_update_rsync_excludes)
  # --delete removes obsolete app files, but never touches excluded paths.
  rsync -a --delete "${args[@]}" "$src"/ "$dst"/
}

ops_update_cache_path() {
  local root="${1:-${ROOT:-.}}"
  printf '%s\n' "$root/.studio-update-cache.json"
}

ops_update_write_cache() {
  local status="$1" remote_ver="${2:-}" archive="${3:-}"
  local cache now
  cache="$(ops_update_cache_path)"
  now="$(date +%s)"
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json,sys; json.dump({"checked_at":int(sys.argv[1]),"status":sys.argv[2],"remote_version":sys.argv[3],"archive_url":sys.argv[4]}, open(sys.argv[5],"w",encoding="utf-8"), indent=2); open(sys.argv[5],"a",encoding="utf-8").write("\n")' \
      "$now" "$status" "$remote_ver" "$archive" "$cache"
  else
    printf '{\n  "checked_at": %s,\n  "status": "%s",\n  "remote_version": "%s",\n  "archive_url": "%s"\n}\n' \
      "$now" "$status" "$remote_ver" "$archive" >"$cache"
  fi
}

ops_update_read_cache() {
  local cache
  cache="$(ops_update_cache_path)"
  [[ -f "$cache" ]] || return 1
  TS_UPDATE_REMOTE_VERSION="$(ops_json_get "$cache" remote_version | tr -d '[:space:]')"
  TS_UPDATE_REMOTE_ARCHIVE="$(ops_json_get "$cache" archive_url | tr -d '[:space:]')"
  TS_UPDATE_STATUS="$(ops_json_get "$cache" status | tr -d '[:space:]')"
  [[ -n "$TS_UPDATE_STATUS" ]]
}

# Sets TS_UPDATE_* globals. Do not capture in $() if you need those globals.
ops_update_check() {
  local force="${1:-0}"
  TS_UPDATE_AVAILABLE=0
  TS_UPDATE_SUMMARY=""
  TS_UPDATE_STATUS="error"
  TS_UPDATE_REMOTE_VERSION=""
  TS_UPDATE_LOCAL_VERSION=""
  TS_UPDATE_REMOTE_ARCHIVE=""

  if ! ops_is_updatable_install; then
    TS_UPDATE_SUMMARY="$(ts_t upd_unsupported)"
    TS_UPDATE_STATUS="unsupported"
    printf '%s\n' "$TS_UPDATE_STATUS"
    return 0
  fi

  command -v curl >/dev/null 2>&1 || {
    TS_UPDATE_SUMMARY="$(ts_t upd_curl_missing)"
    TS_UPDATE_STATUS="error"
    printf '%s\n' "$TS_UPDATE_STATUS"
    return 0
  }

  TS_UPDATE_LOCAL_VERSION="$(ops_local_version | tr -d '[:space:]')"
  [[ -n "$TS_UPDATE_LOCAL_VERSION" ]] || TS_UPDATE_LOCAL_VERSION="0"

  if ! ops_update_should_fetch "$force"; then
    if ops_update_read_cache; then
      if [[ "$TS_UPDATE_STATUS" == "available" && -n "$TS_UPDATE_REMOTE_VERSION" && "$TS_UPDATE_REMOTE_VERSION" != "$TS_UPDATE_LOCAL_VERSION" ]]; then
        TS_UPDATE_AVAILABLE=1
        TS_UPDATE_SUMMARY="$(ts_t upd_summary "$TS_UPDATE_LOCAL_VERSION" "$TS_UPDATE_REMOTE_VERSION")"
        printf '%s\n' "$TS_UPDATE_STATUS"
        return 0
      fi
      if [[ "$TS_UPDATE_STATUS" == "up_to_date" || "$TS_UPDATE_REMOTE_VERSION" == "$TS_UPDATE_LOCAL_VERSION" ]]; then
        TS_UPDATE_SUMMARY="$(ts_t upd_up_to_date "$TS_UPDATE_LOCAL_VERSION")"
        TS_UPDATE_STATUS="up_to_date"
        printf '%s\n' "$TS_UPDATE_STATUS"
        return 0
      fi
    fi
    # No usable cache — fall through to network check.
  fi

  local url tmp
  url="$(ops_update_version_url)"
  tmp="$(mktemp)"
  if ! curl -fsSL --connect-timeout 8 --max-time 30 "$url" -o "$tmp" 2>/dev/null; then
    rm -f "$tmp"
    TS_UPDATE_SUMMARY="$(ts_t upd_offline)"
    TS_UPDATE_STATUS="error"
    printf '%s\n' "$TS_UPDATE_STATUS"
    return 0
  fi
  ops_update_touch_stamp

  TS_UPDATE_REMOTE_VERSION="$(ops_json_get "$tmp" version | tr -d '[:space:]')"
  TS_UPDATE_REMOTE_ARCHIVE="$(ops_json_get "$tmp" archive_url | tr -d '[:space:]')"
  rm -f "$tmp"

  if [[ -z "$TS_UPDATE_REMOTE_VERSION" ]]; then
    TS_UPDATE_SUMMARY="$(ts_t upd_invalid)"
    TS_UPDATE_STATUS="error"
    ops_update_write_cache error "" ""
    printf '%s\n' "$TS_UPDATE_STATUS"
    return 0
  fi

  if [[ "$TS_UPDATE_REMOTE_VERSION" == "$TS_UPDATE_LOCAL_VERSION" ]]; then
    TS_UPDATE_SUMMARY="$(ts_t upd_up_to_date "$TS_UPDATE_LOCAL_VERSION")"
    TS_UPDATE_STATUS="up_to_date"
    ops_update_write_cache up_to_date "$TS_UPDATE_REMOTE_VERSION" "$TS_UPDATE_REMOTE_ARCHIVE"
    printf '%s\n' "$TS_UPDATE_STATUS"
    return 0
  fi

  TS_UPDATE_AVAILABLE=1
  TS_UPDATE_SUMMARY="$(ts_t upd_summary "$TS_UPDATE_LOCAL_VERSION" "$TS_UPDATE_REMOTE_VERSION")"
  TS_UPDATE_STATUS="available"
  ops_update_write_cache available "$TS_UPDATE_REMOTE_VERSION" "$TS_UPDATE_REMOTE_ARCHIVE"
  printf '%s\n' "$TS_UPDATE_STATUS"
}

# Download archive, checksum app tree, replace files (preserve user data), rebuild.
# Sets TS_UPDATE_REEXEC=1 for caller.
ops_update_apply() {
  ts_prog_begin "$(ts_t title_update)"
  ts_prog_plan \
    "check|$(ts_t stage_check)|15" \
    "stop|$(ts_t stage_stop)|25" \
    "download|$(ts_t stage_download)|40" \
    "verify|$(ts_t stage_verify)|30" \
    "apply|$(ts_t stage_apply)|25" \
    "rebuild|$(ts_t stage_rebuild)|120"

  ts_prog_enter check "$(ts_t status_read_remote)"
  ops_find_root_quiet || ops_resolve_root || ui_die "$(ts_t err_install_not_found)"
  cd "$ROOT"
  export TS_ROOT="$ROOT"

  ops_is_updatable_install || ui_die "$(ts_t err_update_dev "$INSTALL_DIR")"

  ops_update_check force >/dev/null
  local status="${TS_UPDATE_STATUS:-error}"
  case "$status" in
    up_to_date)
      ts_prog_status "$(ts_t status_up_to_date "$TS_UPDATE_LOCAL_VERSION")"
      ts_prog_done
      return 0
      ;;
    available) ;;
    unsupported)
      ui_die "${TS_UPDATE_SUMMARY:-$(ts_t upd_unsupported)}"
      ;;
    *)
      ui_die "$(ts_t err_update_check "${TS_UPDATE_SUMMARY:-unknown error}")"
      ;;
  esac

  local remote_ver="$TS_UPDATE_REMOTE_VERSION"
  local archive_url="$TS_UPDATE_REMOTE_ARCHIVE"
  if [[ -z "$archive_url" ]]; then
    archive_url="https://codeload.github.com/DDoSKudya/task-studio/tar.gz/refs/heads/${REPO_BRANCH}"
  fi

  if [[ "$(ops_stack_state)" == "running" ]]; then
    ts_prog_enter stop "$(ts_t status_stop_before_update)"
    ops_need_docker
    ops_ensure_stopped || ui_die "$(ts_t err_stop_before_update)"
  else
    ts_prog_enter stop "$(ts_t status_already_stopped)"
  fi

  ts_prog_enter download "$(ts_t status_downloading_ver "$remote_ver")"
  command -v curl >/dev/null 2>&1 || ui_die "$(ts_t err_curl)"
  command -v tar >/dev/null 2>&1 || ui_die "$(ts_t err_tar)"
  local work archive payload
  work="$(mktemp -d "${TMPDIR:-/tmp}/task-studio-update.XXXXXX")"
  archive="$work/src.tgz"
  if ! curl -fsSL --connect-timeout 15 --max-time 600 "$archive_url" -o "$archive"; then
    rm -rf "$work"
    ui_die "$(ts_t err_download)"
  fi
  mkdir -p "$work/extract"
  if ! tar -xzf "$archive" -C "$work/extract"; then
    rm -rf "$work"
    ui_die "$(ts_t err_unpack)"
  fi
  payload="$(find "$work/extract" -mindepth 1 -maxdepth 1 -type d | head -1)"
  if [[ -z "$payload" || ! -f "$payload/studio-version.json" ]]; then
    rm -rf "$work"
    ui_die "$(ts_t err_layout)"
  fi

  ts_prog_enter verify "$(ts_t status_compare_hash)"
  local old_hash new_hash
  old_hash="$(ops_content_sha256 "$ROOT")"
  new_hash="$(ops_content_sha256 "$payload")"
  if [[ -z "$new_hash" ]]; then
    rm -rf "$work"
    ui_die "$(ts_t err_fingerprint)"
  fi

  export TS_UPDATE_REEXEC=1

  if [[ "$old_hash" == "$new_hash" ]]; then
    ts_prog_enter apply "$(ts_t status_hash_same)"
    ops_write_state "$remote_ver" "$new_hash"
    ops_mark_consumer "$ROOT"
  else
    ts_prog_enter apply "$(ts_t status_replace_files)"
    local env_before=""
    [[ -f "$ROOT/.env" ]] && env_before="$(wc -c <"$ROOT/.env" | tr -d ' ')"
    if ! ops_sync_payload "$payload" "$ROOT"; then
      rm -rf "$work"
      ui_die "$(ts_t err_sync)"
    fi
    if [[ -n "$env_before" ]]; then
      [[ -f "$ROOT/.env" ]] || { rm -rf "$work"; ui_die "$(ts_t err_env_gone)"; }
    fi
    [[ -d "$ROOT/data" ]] || mkdir -p "$ROOT/data"
    ops_write_state "$remote_ver" "$new_hash"
    ops_mark_consumer "$ROOT"
  fi
  rm -rf "$work"
  work=""

  ts_prog_enter rebuild "$(ts_t status_rebuild)"
  if [[ ! -f .env ]]; then
    ts_prog_status "$(ts_t status_no_env)"
    ts_prog_done
    return 0
  fi
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1
  ops_need_docker
  local profile_args
  profile_args="$(profiles_args | tr '\n' ' ')"
  # shellcheck disable=SC2086
  if ! ops_compose $profile_args build; then
    ui_die "$(ts_t err_build_update)"
  fi
  # shellcheck disable=SC2086
  if ! ops_compose $profile_args up -d --remove-orphans; then
    ui_die "$(ts_t err_up_update)"
  fi
  if wait_app_ready 90 5; then
    open_app_ui "$APP_UI_URL" || true
  else
    ui_warn "$(ts_t warn_ui_after_update "$APP_UI_URL")"
  fi
  ensure_script_permissions "$ROOT"
  create_desktop_shortcuts "$ROOT" || true
  ts_prog_done
}
