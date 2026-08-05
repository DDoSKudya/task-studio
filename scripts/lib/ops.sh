
REPO_SSH="${TASK_STUDIO_REPO_SSH:-git@github.com:DDoSKudya/task-studio.git}"
REPO_HTTPS="${TASK_STUDIO_REPO_HTTPS:-https://github.com/DDoSKudya/task-studio.git}"
REPO_BRANCH="${TASK_STUDIO_BRANCH:-develop}"
INSTALL_DIR="${TASK_STUDIO_DIR:-$HOME/task-studio}"
MIN_RAM_GB="${TASK_STUDIO_MIN_RAM_GB:-8}"
OLLAMA_MODEL_DEFAULT="${OLLAMA_MODEL:-qwen2.5:3b}"

ops_docker_ready() {
  docker info >/dev/null 2>&1
}

ops_try_start_docker() {
  [[ "${TASK_STUDIO_NO_AUTO_DOCKER:-}" == "1" ]] && return 1
  local os
  os="$(uname -s 2>/dev/null || echo unknown)"

  case "$os" in
    Linux)
      if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-unit-files 2>/dev/null | grep -q '^docker\.service'; then
          if sudo -n systemctl start docker >/dev/null 2>&1; then
            return 0
          fi
          if systemctl start docker >/dev/null 2>&1; then
            return 0
          fi
        fi
        if systemctl --user start docker-desktop >/dev/null 2>&1; then
          return 0
        fi
      fi
      if command -v service >/dev/null 2>&1; then
        if sudo -n service docker start >/dev/null 2>&1; then
          return 0
        fi
      fi
      if command -v docker-desktop >/dev/null 2>&1; then
        nohup docker-desktop >/dev/null 2>&1 &
        disown 2>/dev/null || true
        return 0
      fi
      if [[ -x /opt/docker-desktop/bin/docker-desktop ]]; then
        nohup /opt/docker-desktop/bin/docker-desktop >/dev/null 2>&1 &
        disown 2>/dev/null || true
        return 0
      fi
      ;;
    Darwin)
      if [[ -d /Applications/Docker.app ]]; then
        open -a Docker >/dev/null 2>&1 && return 0
      fi
      ;;
  esac
  return 1
}

ops_wait_docker() {
  local timeout="${TASK_STUDIO_DOCKER_WAIT_SEC:-120}"
  local i=0
  [[ "$timeout" =~ ^[0-9]+$ ]] || timeout=120
  ((timeout < 15)) && timeout=15
  while ((i < timeout)); do
    if ops_docker_ready; then
      return 0
    fi
    if ((i % 10 == 0)); then
      if declare -f ts_prog_status >/dev/null 2>&1 && ts_prog_active 2>/dev/null; then
        ts_prog_status "$(ts_t status_docker_waiting "$i" "$timeout")"
      elif declare -f ui_info >/dev/null 2>&1; then
        ui_info "$(ts_t status_docker_waiting "$i" "$timeout")"
      fi
    fi
    sleep 2
    i=$((i + 2))
  done
  return 1
}

ops_need_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    ui_die "$(ts_t err_docker_missing)"
  fi

  if ! ops_docker_ready; then
    if declare -f ts_prog_status >/dev/null 2>&1 && ts_prog_active 2>/dev/null; then
      ts_prog_status "$(ts_t status_docker_starting)"
    elif declare -f ui_info >/dev/null 2>&1; then
      ui_info "$(ts_t status_docker_starting)"
    fi
    if ops_try_start_docker; then
      :
    else
      true
    fi
    if ! ops_wait_docker; then
      local info_err=""
      info_err="$(docker info 2>&1 >/dev/null || true)"
      if [[ -n "${info_err//[[:space:]]/}" ]]; then
        ui_die "$(ts_t err_docker_unusable "$info_err")"
      fi
      ui_die "$(ts_t err_docker_start_failed)"
    fi
  fi

  if ! docker compose version >/dev/null 2>&1; then
    ui_die "$(ts_t err_compose_missing)"
  fi
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1
  local ver major
  ver="$(docker version --format '{{.Server.Version}}' 2>/dev/null || true)"
  major="${ver%%.*}"
  if [[ "$major" =~ ^[0-9]+$ ]] && ((major < 20)); then
    ui_die "$(ts_t err_buildkit "$ver")"
  fi
}

ops_default_parallel_limit() {
  local ram
  ram="$(ops_detect_ram_gb 2>/dev/null || echo 0)"
  if [[ "$ram" -gt 0 && "$ram" -le 8 ]]; then
    printf '1\n'
  elif [[ "$ram" -gt 0 && "$ram" -le 12 ]]; then
    printf '2\n'
  elif [[ "$ram" -gt 0 && "$ram" -le 16 ]]; then
    printf '3\n'
  else
    printf '4\n'
  fi
}

ops_warn_install_path() {
  local root="${1:-$(pwd -P)}"
  case "$root" in
    /mnt/[a-zA-Z]/*|/mnt/[a-zA-Z])
      ui_warn "$(ts_t warn_path_wsl_mnt "$root")"
      ;;
  esac
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

  systok=""
  if command -v python3 >/dev/null 2>&1; then
    systok="$(python3 - <<'PY'
import re, pathlib, secrets
text = pathlib.Path(".env").read_text(encoding="utf-8")
m = re.search(r"^ORCHESTRATOR_SYSTEM_TOKEN=(.*)$", text, re.M)
raw = (m.group(1).strip().strip('"').strip("'") if m else "")
if not raw or len(raw) < 16:
    print(secrets.token_urlsafe(32))
PY
)"
  fi
  if [[ -n "${systok:-}" ]]; then
    if grep -q '^ORCHESTRATOR_SYSTEM_TOKEN=' .env; then
      sed -i.bak "s|^ORCHESTRATOR_SYSTEM_TOKEN=.*|ORCHESTRATOR_SYSTEM_TOKEN=$systok|" .env
    else
      printf '\nORCHESTRATOR_SYSTEM_TOKEN=%s\n' "$systok" >> .env
    fi
    rm -f .env.bak
    ui_info "Generated ORCHESTRATOR_SYSTEM_TOKEN"
  fi

  grafpw=""
  if command -v python3 >/dev/null 2>&1; then
    grafpw="$(python3 - <<'PY'
import re, pathlib, secrets
text = pathlib.Path(".env").read_text(encoding="utf-8")
m = re.search(r"^GRAFANA_ADMIN_PASSWORD=(.*)$", text, re.M)
raw = (m.group(1).strip().strip('"').strip("'") if m else "")
if not raw or raw == "admin":
    print(secrets.token_urlsafe(16))
PY
)"
  fi
  if [[ -n "${grafpw:-}" ]]; then
    if grep -q '^GRAFANA_ADMIN_PASSWORD=' .env; then
      sed -i.bak "s|^GRAFANA_ADMIN_PASSWORD=.*|GRAFANA_ADMIN_PASSWORD=$grafpw|" .env
    else
      printf '\nGRAFANA_ADMIN_PASSWORD=%s\n' "$grafpw" >> .env
    fi
    rm -f .env.bak
    ui_info "Generated GRAFANA_ADMIN_PASSWORD"
  fi

  if grep -q '^OLLAMA_MODEL=' .env; then
    if grep -qE '^OLLAMA_MODEL=\s*$|^OLLAMA_MODEL=llama3\.2\s*$' .env; then
      sed -i.bak "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$OLLAMA_MODEL_DEFAULT|" .env
      rm -f .env.bak
    fi
  else
    printf '\nOLLAMA_MODEL=%s\n' "$OLLAMA_MODEL_DEFAULT" >> .env
  fi

  if grep -q '^PACK_MAX_UPLOAD_MB=' .env; then
    if grep -qE '^PACK_MAX_UPLOAD_MB=\s*$' .env; then
      sed -i.bak "s|^PACK_MAX_UPLOAD_MB=.*|PACK_MAX_UPLOAD_MB=500|" .env
      rm -f .env.bak
    fi
  else
    printf '\nPACK_MAX_UPLOAD_MB=500\n' >> .env
  fi

  if [[ "$(uname -s)" == "Linux" ]]; then
    gid=""
    if command -v getent >/dev/null 2>&1; then
      gid="$(getent group docker 2>/dev/null | cut -d: -f3 || true)"
    fi
    if [[ -z "${gid:-}" ]] && [[ -S /var/run/docker.sock ]] && command -v stat >/dev/null 2>&1; then
      gid="$(stat -c '%g' /var/run/docker.sock 2>/dev/null || true)"
    fi
    if [[ -n "${gid:-}" ]]; then
      if grep -q '^DOCKER_GID=' .env; then
        sed -i.bak "s|^DOCKER_GID=.*|DOCKER_GID=$gid|" .env
      else
        printf '\nDOCKER_GID=%s\n' "$gid" >> .env
      fi
      rm -f .env.bak
    fi
  fi

  # P321: HTTPS UI → Secure cookie (не трогаем явный false на http).
  ui_url="${TASK_STUDIO_UI_URL:-http://localhost}"
  case "${ui_url}" in
    https://*|HTTPS://*)
      if grep -q '^COOKIE_SECURE=' .env; then
        sed -i.bak 's|^COOKIE_SECURE=.*|COOKIE_SECURE=true|' .env
      else
        printf '\nCOOKIE_SECURE=true\n' >> .env
      fi
      rm -f .env.bak
      ;;
  esac

  preferred_was_80=1
  prev_port="$(ts_http_port_from_env_file)"
  if [[ "$prev_port" =~ ^[0-9]+$ && "$prev_port" != "80" ]]; then
    preferred_was_80=0
  fi
  if [[ "${TASK_STUDIO_HTTP_PORT:-}" =~ ^[0-9]+$ && "${TASK_STUDIO_HTTP_PORT}" != "80" ]]; then
    preferred_was_80=0
  fi
  port="$(resolve_ts_http_port)" || ui_die "No free HTTP port for Task Studio UI"
  if grep -q '^TASK_STUDIO_HTTP_PORT=' .env; then
    sed -i.bak "s|^TASK_STUDIO_HTTP_PORT=.*|TASK_STUDIO_HTTP_PORT=$port|" .env
  else
    printf '\nTASK_STUDIO_HTTP_PORT=%s\n' "$port" >> .env
  fi
  rm -f .env.bak
  file_ui="$(grep -E '^TASK_STUDIO_UI_URL=' .env 2>/dev/null | head -1 | cut -d= -f2- | sed "s/[\"'[:space:]]//g" || true)"
  case "${file_ui}" in
    ''|http://localhost|http://localhost:*|http://127.0.0.1|http://127.0.0.1:*|https://localhost|https://localhost:*|https://127.0.0.1|https://127.0.0.1:*)
      ui_val="$(ts_format_ui_url "$port")"
      if grep -q '^TASK_STUDIO_UI_URL=' .env; then
        sed -i.bak "s|^TASK_STUDIO_UI_URL=.*|TASK_STUDIO_UI_URL=$ui_val|" .env
      else
        printf '\nTASK_STUDIO_UI_URL=%s\n' "$ui_val" >> .env
      fi
      rm -f .env.bak
      ;;
  esac
  probe_val="$(ts_format_ui_probe_url "$port")"
  if grep -q '^TASK_STUDIO_UI_PROBE_URL=' .env; then
    sed -i.bak "s|^TASK_STUDIO_UI_PROBE_URL=.*|TASK_STUDIO_UI_PROBE_URL=$probe_val|" .env
  else
    printf '\nTASK_STUDIO_UI_PROBE_URL=%s\n' "$probe_val" >> .env
  fi
  rm -f .env.bak
  ts_sync_ui_endpoint_vars "$port"
  if [[ "$preferred_was_80" -eq 1 && "$port" != "80" ]]; then
    ui_info "$(ts_t info_http_port_fallback "$port")"
  fi
}

ops_prepare_dirs() {
  mkdir -p \
    data/postgres data/redis data/rabbitmq data/packs \
    data/meilisearch data/clickhouse data/minio data/ollama \
    data/grafana data/prometheus data/piston/packages \
    data/logs
  chmod -R a+rwX data/packs 2>/dev/null || true
  chmod a+rwX data/logs 2>/dev/null || true
  if [[ ! -w data/logs ]]; then
    mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/task-studio/logs" 2>/dev/null || true
  fi
}

ops_compose() {
  if [[ -f .env ]]; then
    local pname http_port
    pname="$(grep -E '^COMPOSE_PROJECT_NAME=' .env 2>/dev/null | head -1 | cut -d= -f2- | sed "s/[\"'[:space:]]//g" || true)"
    if [[ -n "$pname" ]]; then
      export COMPOSE_PROJECT_NAME="$pname"
    fi
    http_port="$(ts_http_port_from_env_file)"
    if [[ "$http_port" =~ ^[0-9]+$ ]]; then
      export TASK_STUDIO_HTTP_PORT="$http_port"
    fi
  fi
  export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-task-studio}"
  export TASK_STUDIO_HTTP_PORT="${TASK_STUDIO_HTTP_PORT:-80}"
  export COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT:-$(ops_default_parallel_limit)}"
  export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"
  export COMPOSE_DOCKER_CLI_BUILD="${COMPOSE_DOCKER_CLI_BUILD:-1}"
  docker compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" --env-file .env "$@"
}

ops_compose_container_name() {
  local service="$1"
  local pname="${COMPOSE_PROJECT_NAME:-task-studio}"
  local name=""
  name="$(
    ops_compose ps -a --format '{{.Name}}' "$service" 2>/dev/null | head -1 | tr -d '\r'
  )"
  if [[ -z "$name" ]]; then
    name="$(
      docker ps -a \
        --filter "label=com.docker.compose.project=${pname}" \
        --filter "label=com.docker.compose.service=${service}" \
        --format '{{.Names}}' 2>/dev/null | head -1 | tr -d '\r'
    )"
  fi
  if [[ -z "$name" ]]; then
    name="${pname}-${service}-1"
  fi
  printf '%s\n' "$name"
}

ops_dump_compose_failure() {
  local log="${TS_PROGRESS_LOG:-}"
  local pname="${COMPOSE_PROJECT_NAME:-task-studio}"
  local names name status dumped="" svc
  if [[ -z "$log" ]]; then
    if [[ -n "${TS_LOG_FILE:-}" ]]; then
      log="$TS_LOG_FILE"
    elif [[ -w data/logs/studio-last.log ]]; then
      log="data/logs/studio-last.log"
    fi
  fi
  if [[ -z "$log" ]]; then
    return 0
  fi
  {
    printf '\n===== compose failure diagnostics =====\n'
    printf 'project=%s time=%s\n' "$pname" "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date)"
    ops_compose ps -a 2>&1 || true
    printf '\n'
  } >>"$log" 2>/dev/null || true

  for svc in catalog auth postgres grading; do
    name="$(ops_compose_container_name "$svc")"
    dumped+=" ${name} "
    if docker inspect "$name" >/dev/null 2>&1; then
      status="$(docker inspect --format '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$name" 2>/dev/null || true)"
      {
        printf '\n----- logs: %s (%s) -----\n' "$name" "$status"
        docker logs --tail 200 "$name" 2>&1 || true
      } >>"$log" 2>/dev/null || true
    fi
  done

  names="$(
    docker ps -a --filter "label=com.docker.compose.project=${pname}" \
      --format '{{.Names}}\t{{.Status}}' 2>/dev/null || true
  )"
  while IFS=$'\t' read -r name status; do
    [[ -z "$name" ]] && continue
    case "$status" in
      *unhealthy*|*Exited*|*Dead*|*Restarting*)
        case "$dumped" in
          *" ${name} "*) continue ;;
        esac
        {
          printf '\n----- logs: %s (%s) -----\n' "$name" "$status"
          docker logs --tail 150 "$name" 2>&1 || true
        } >>"$log" 2>/dev/null || true
        ;;
    esac
  done <<<"$names"
}

ops_wait_catalog_healthy() {
  local timeout="${1:-180}"
  local name
  name="$(ops_compose_container_name catalog)"
  local i=0 health status
  while ((i < timeout)); do
    if docker inspect "$name" >/dev/null 2>&1; then
      health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$name" 2>/dev/null || true)"
      if [[ "$health" == "healthy" ]]; then
        return 0
      fi
      if [[ "$health" == "unhealthy" ]]; then
        ops_dump_compose_failure
        return 1
      fi
      status="$(docker inspect --format '{{.State.Status}}' "$name" 2>/dev/null || true)"
      if [[ "$status" == "exited" || "$status" == "dead" ]]; then
        ops_dump_compose_failure
        return 1
      fi
    fi
    sleep 3
    i=$((i + 3))
  done
  ops_dump_compose_failure
  return 1
}

ops_compose_up() {
  # shellcheck disable=SC2086
  local profile_args="$*"
  if declare -f ts_prog_status >/dev/null 2>&1 && ts_prog_active 2>/dev/null; then
    ts_prog_status "$(ts_t status_starting_infra 2>/dev/null || echo "Starting data services…")"
  fi
  # shellcheck disable=SC2086
  ops_compose $profile_args up -d postgres redis rabbitmq minio meilisearch 2>/dev/null || true
  # shellcheck disable=SC2086
  if ! ops_compose $profile_args up -d --wait --wait-timeout 180 postgres redis rabbitmq; then
    ops_dump_compose_failure
    return 1
  fi
  if declare -f ts_prog_status >/dev/null 2>&1 && ts_prog_active 2>/dev/null; then
    ts_prog_status "$(ts_t status_starting_catalog 2>/dev/null || echo "Starting catalog…")"
  fi
  # shellcheck disable=SC2086
  ops_compose $profile_args up -d --no-deps catalog || true
  local catalog_ok=0
  if ops_wait_catalog_healthy 240; then
    catalog_ok=1
  else
    # shellcheck disable=SC2086
    ops_compose $profile_args up -d --force-recreate --no-deps catalog || true
    if ops_wait_catalog_healthy 240; then
      catalog_ok=1
    fi
  fi
  if [[ "$catalog_ok" -ne 1 ]]; then
    if declare -f ui_warn >/dev/null 2>&1; then
      ui_warn "$(ts_t warn_catalog_continue 2>/dev/null || echo "catalog is not healthy — continuing with the rest of the stack")"
    fi
    ops_dump_compose_failure
  fi
  if declare -f ts_prog_status >/dev/null 2>&1 && ts_prog_active 2>/dev/null; then
    ts_prog_status "$(ts_t status_starting_containers)"
  fi
  # shellcheck disable=SC2086
  if ops_compose $profile_args up -d --remove-orphans; then
    return 0
  fi
  sleep 10
  # shellcheck disable=SC2086
  if ops_compose $profile_args up -d --remove-orphans; then
    return 0
  fi
  ops_dump_compose_failure
  return 1
}

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
    ops_compose --profile full --profile editor --profile host-metrics \
      ps --format '{{.State}}' 2>/dev/null \
      | grep -ciE 'running|healthy' || true
  )"
  [[ "$n" =~ ^[0-9]+$ ]] || n=0
  printf '%s\n' "$n"
}

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

ops_ensure_stopped() {
  [[ -f "$COMPOSE_FILE" ]] || return 0
  local down_out=""
  if [[ -f .env ]]; then
    down_out="$(ops_compose --profile full --profile editor --profile host-metrics \
      down --remove-orphans 2>&1)" || true
  else
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-task-studio}"
    down_out="$(docker compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" \
      --profile full --profile editor --profile host-metrics \
      down --remove-orphans 2>&1)" || true
  fi
  if [[ -n "$down_out" ]]; then
    printf '%s\n' "$down_out" >>"${TS_PROGRESS_LOG:-/dev/null}" 2>/dev/null || true
  fi
  if docker compose -p deploy -f "$COMPOSE_FILE" ps -q 2>/dev/null | grep -q .; then
    docker compose -p deploy -f "$COMPOSE_FILE" \
      --profile full --profile editor --profile host-metrics \
      down --remove-orphans >>"${TS_PROGRESS_LOG:-/dev/null}" 2>&1 || true
  fi
  local n left=30
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

ops_detect_ollama_accelerator() {
  local requested="${OLLAMA_ACCELERATOR:-auto}"
  if [[ "$requested" == "cpu" || "$requested" == "gpu" ]]; then
    printf '%s' "$requested"
    return 0
  fi
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    printf '%s' "gpu"
    return 0
  fi
  printf '%s' "cpu"
}

ops_configure_ollama_profile() {
  local accel profile
  accel="$(ops_detect_ollama_accelerator)"
  profile="${OLLAMA_PROFILE:-}"
  if [[ -z "$profile" ]]; then
    case "$accel" in
      gpu) profile="gpu-balanced" ;;
      *) profile="cpu-balanced" ;;
    esac
  fi
  export OLLAMA_GPU_AVAILABLE="$([[ "$accel" == "gpu" ]] && echo 1 || echo 0)"
  export OLLAMA_ACCELERATOR="${OLLAMA_ACCELERATOR:-auto}"
  export OLLAMA_PROFILE="$profile"
  if [[ -f .env ]]; then
    grep -q '^OLLAMA_GPU_AVAILABLE=' .env \
      && sed -i.bak "s|^OLLAMA_GPU_AVAILABLE=.*|OLLAMA_GPU_AVAILABLE=$OLLAMA_GPU_AVAILABLE|" .env \
      || printf '\nOLLAMA_GPU_AVAILABLE=%s\n' "$OLLAMA_GPU_AVAILABLE" >> .env
    grep -q '^OLLAMA_PROFILE=' .env \
      && sed -i.bak "s|^OLLAMA_PROFILE=.*|OLLAMA_PROFILE=$OLLAMA_PROFILE|" .env \
      || printf '\nOLLAMA_PROFILE=%s\n' "$OLLAMA_PROFILE" >> .env
  fi
}

ops_pull_ollama() {
  ops_configure_ollama_profile
  local model
  model="$(grep -E '^OLLAMA_MODEL=' .env | head -1 | cut -d= -f2- | tr -d '[:space:]')"
  model="${model:-$OLLAMA_MODEL_DEFAULT}"
  ui_info "$(ts_t info_pull_model "$model")"
  ops_compose --profile full exec -T ollama ollama pull "$model" \
    || ui_warn "$(ts_t warn_model_pull "$COMPOSE_FILE" "$model")"
  local embed
  embed="$(grep -E '^OLLAMA_MODEL_EMBED=' .env | head -1 | cut -d= -f2- | tr -d '[:space:]')"
  embed="${embed:-nomic-embed-text}"
  if [[ -n "$embed" && "$embed" != "$model" ]]; then
    ops_compose --profile full exec -T ollama ollama pull "$embed" \
      || ui_warn "$(ts_t warn_model_pull "$COMPOSE_FILE" "$embed")"
  fi
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

ops_install_is_repair() {
  [[ "$(ops_stack_state)" != "missing" ]]
}

ops_install_title() {
  if ops_install_is_repair; then
    ts_t title_rebuild_packages
  else
    ts_t title_install
  fi
}

ops_install() {
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1

  local repair=0
  if ops_install_is_repair; then
    repair=1
  fi

  ts_prog_begin "$(ops_install_title)"
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
  ts_prog_status "$(ts_t status_build_parallel "$(ops_default_parallel_limit)")"

  ts_prog_status "$(ts_t status_ensure_repo)"
  ops_ensure_repo
  cd "$ROOT"
  export TS_ROOT="$ROOT"
  ops_warn_install_path "$ROOT"
  ops_ensure_env
  if [[ "$ram" -gt 0 && "$ram" -lt 16 ]]; then
    if grep -qE '^ORCHESTRATOR_MODE=' .env; then
      sed -i.bak "s|^ORCHESTRATOR_MODE=.*|ORCHESTRATOR_MODE=${ORCHESTRATOR_MODE}|" .env
    else
      printf '\nORCHESTRATOR_MODE=%s\n' "${ORCHESTRATOR_MODE}" >> .env
    fi
    rm -f .env.bak
  fi
  ops_prepare_dirs

  local profile_args
  profile_args="$(profiles_args | tr '\n' ' ')"
  if ! can_use_host_metrics; then
    ts_prog_status "$(ts_t status_skip_metrics)"
  fi

  if [[ "$repair" -eq 1 ]]; then
    ts_prog_enter build "$(ts_t status_build)"
  else
    ts_prog_enter build "$(ts_t status_build_slow)"
  fi
  # shellcheck disable=SC2086
  if ! ops_compose $profile_args build; then
    ui_die "$(ts_t err_build)"
  fi

  ts_prog_enter start "$(ts_t status_starting_containers)"
  # shellcheck disable=SC2086
  if ! ops_compose_up $profile_args; then
    ui_die "$(ts_t err_up)"
  fi

  ts_prog_enter health "$(ts_t status_waiting_ui "$APP_UI_PROBE_URL")"
  if wait_app_ready 90 5; then
    ts_prog_status "$(ts_t status_ui_ok)"
  else
    ui_die "$(ts_ui_failure_hint "$APP_UI_URL")"
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
  ops_ensure_env

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
  if ! ops_compose_up $profile_args; then
    ui_die "$(ts_t err_up_short)"
  fi

  ts_prog_enter health "$(ts_t status_check_ui "$APP_UI_PROBE_URL")"
  if wait_app_ready 60 3; then
    ts_prog_status "$(ts_t status_ui_ok)"
    ts_prog_done
  else
    ui_die "$(ts_ui_failure_hint "$APP_UI_URL")"
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
  ops_ensure_env
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
  if ! ops_compose_up $profile_args; then
    ui_die "$(ts_t err_up_after_restart)"
  fi

  ts_prog_enter health "$(ts_t status_check_ui "$APP_UI_PROBE_URL")"
  if wait_app_ready 60 3; then
    ts_prog_status "$(ts_t status_ui_ok)"
    ts_prog_done
  else
    ui_die "$(ts_ui_failure_hint "$APP_UI_URL")"
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
  if [[ -n "${TS_UNINSTALL_EXIT_FILE:-}" ]]; then
    printf '1\n' >"$TS_UNINSTALL_EXIT_FILE" 2>/dev/null || true
  fi
  printf '1\n' >"$root/.studio-uninstall-exit" 2>/dev/null || true
  if [[ -n "${TS_PROGRESS_FILE:-}" ]]; then
    ts_prog_write "uninstall_exit=1"
  fi
  ts_prog_status "$(ts_t status_delete_scheduled "$root")"
}

ops_uninstall_confirm() {
  local yes=0 purge=0 arg
  TS_UNINSTALL_EXIT=0
  TS_UNINSTALL_PURGE=0
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
        return 2
        ;;
      *) ui_die "$(ts_t err_unknown_opt "$arg")" ;;
    esac
  done
  if [[ "${TASK_STUDIO_UNINSTALL_YES:-}" == "1" ]]; then
    yes=1
  fi

  ops_resolve_root || ui_die "$(ts_t err_install_not_found)"
  export TS_ROOT="$ROOT"
  rm -f "$ROOT/.studio-uninstall-exit" 2>/dev/null || true
  TS_UNINSTALL_EXIT_FILE="$(mktemp "${TMPDIR:-/tmp}/ts-uninstall-exit.XXXXXX")"
  export TS_UNINSTALL_EXIT_FILE
  : >"$TS_UNINSTALL_EXIT_FILE"

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
      if ! ui_confirm_delete "$(ts_t confirm_uninstall)"; then
        ui_info "$(ts_t info_cancelled)"
        return 1
      fi
    else
      if ! ui_confirm_delete "$(ts_t confirm_uninstall)"; then
        ui_info "$(ts_t info_cancelled)"
        return 1
      fi
      if ui_confirm "$(ts_t confirm_purge)"; then
        purge=1
        ui_warn "$(ts_t warn_purge "$ROOT")"
      fi
    fi
  fi

  TS_UNINSTALL_PURGE="$purge"
  export TS_UNINSTALL_PURGE
  return 0
}

ops_uninstall_run() {
  local purge="${TS_UNINSTALL_PURGE:-0}"

  ops_resolve_root || ui_die "$(ts_t err_install_not_found)"
  export TS_ROOT="$ROOT"
  if ops_is_consumer_root "$ROOT"; then
    purge=1
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
    ops_compose --profile full --profile editor --profile host-metrics \
      down -v --rmi local --remove-orphans || true
  else
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-task-studio}"
    docker compose -p "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" \
      --profile full --profile editor --profile host-metrics \
      down -v --rmi local --remove-orphans || true
  fi
  if docker compose -p deploy -f "$COMPOSE_FILE" ps -q 2>/dev/null | grep -q .; then
    docker compose -p deploy -f "$COMPOSE_FILE" \
      --profile full --profile editor --profile host-metrics \
      down -v --rmi local --remove-orphans || true
  fi

  ts_prog_enter files "$(ts_t status_remove_files)"
  remove_desktop_shortcuts || true

  ts_prog_enter finish "$(ts_t status_cleanup)"
  if [[ "$purge" -eq 1 ]]; then
    if ops_safe_purge_root "$ROOT"; then
      ops_schedule_delete_root "$ROOT"
    else
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

ops_uninstall() {
  local rc
  ops_uninstall_confirm "$@"
  rc=$?
  [[ "$rc" -eq 2 ]] && return 0
  [[ "$rc" -ne 0 ]] && return 1
  ops_uninstall_run
}

ops_uninstall_should_exit() {
  if [[ -n "${TS_UNINSTALL_EXIT_FILE:-}" && -f "$TS_UNINSTALL_EXIT_FILE" ]]; then
    local flag
    flag="$(tr -d '[:space:]' <"$TS_UNINSTALL_EXIT_FILE" 2>/dev/null || true)"
    rm -f "$TS_UNINSTALL_EXIT_FILE" 2>/dev/null || true
    unset TS_UNINSTALL_EXIT_FILE
    if [[ "$flag" == "1" ]]; then
      TS_UNINSTALL_EXIT=1
      return 0
    fi
  fi
  local root="${ROOT:-${TS_ROOT:-}}"
  if [[ -z "$root" ]]; then
    ops_find_root_quiet 2>/dev/null || true
    root="${ROOT:-}"
  fi
  if [[ -n "$root" && -f "$root/.studio-uninstall-exit" ]]; then
    rm -f "$root/.studio-uninstall-exit" 2>/dev/null || true
    TS_UNINSTALL_EXIT=1
    return 0
  fi
  [[ "${TS_UNINSTALL_EXIT:-0}" == "1" ]]
}

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
  local src="$1" key="$2"
  if command -v python3 >/dev/null 2>&1; then
    if [[ "$src" == "-" ]]; then
      python3 -c 'import json,sys; d=json.load(sys.stdin); v=d.get(sys.argv[1],""); print(v if v is not None else "")' "$key"
    else
      python3 -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8")); v=d.get(sys.argv[2],""); print(v if v is not None else "")' "$src" "$key"
    fi
    return
  fi
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

ops_is_updatable_install() {
  local root want
  root="$(pwd -P)"
  [[ -f "$root/.studio-consumer" ]] && return 0
  [[ "${TASK_STUDIO_ALLOW_SELF_UPDATE:-0}" == "1" ]] && return 0
  want="$(cd "$INSTALL_DIR" 2>/dev/null && pwd -P || true)"
  [[ -n "$want" && "$root" == "$want" ]]
}

ops_content_sha256() {
  local root="$1"
  (
    cd "$root" || exit 1
    # shellcheck disable=SC2016
    find . -type f \
      ! -path './data/*' \
      ! -path './.git/*' \
      ! -path './.cursor/*' \
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

ops_update_preserve_paths() {
  printf '%s\n' \
    'data' \
    '.env' \
    '.env.local' \
    '.studio-update-check' \
    '.studio-state.json' \
    '.studio-consumer' \
    '.git' \
    'compose.override.yml' \
    'docker-compose.override.yml'
}

ops_sync_payload() {
  local src="$1" dst="$2"
  command -v tar >/dev/null 2>&1 || ui_die "$(ts_t err_tar)"

  local parent base work newroot preserve backup rel lock
  parent="$(dirname "$dst")"
  base="$(basename "$dst")"
  lock="$parent/.task-studio-update.lock"
  work="$parent/.task-studio-update.$$"
  newroot="$work/newroot"
  preserve="$work/preserve"
  backup="$work/backup"

  exec 9>"$lock"
  if ! flock -n 9; then
    ui_die "$(ts_t err_update_in_progress 2>/dev/null || echo 'update already in progress')"
  fi

  rm -rf "$work"
  mkdir -p "$newroot" "$preserve"

  if ! tar -C "$src" -cf - . | tar -C "$newroot" -xf -; then
    rm -rf "$work"
    return 1
  fi

  while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    [[ -e "$dst/$rel" ]] || continue
    mkdir -p "$preserve/$(dirname "$rel")" "$newroot/$(dirname "$rel")"
    mv "$dst/$rel" "$preserve/$rel"
    mv "$preserve/$rel" "$newroot/$rel"
  done < <(ops_update_preserve_paths)

  if ! mv "$dst" "$backup"; then
    rm -rf "$work"
    return 1
  fi

  if ! mv "$newroot" "$dst"; then
    rm -rf "$dst"
    mv "$backup" "$dst" 2>/dev/null || true
    rm -rf "$work"
    return 1
  fi

  cd "$dst" || {
    rm -rf "$backup" "$work"
    return 1
  }
  rm -rf "$backup" "$work"
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
  if ! ops_compose_up $profile_args; then
    ui_die "$(ts_t err_up_update)"
  fi
  if wait_app_ready 90 5; then
    ts_prog_status "$(ts_t status_ui_ok)"
  else
    ui_warn "$(ts_ui_failure_hint "$APP_UI_URL")"
  fi
  ensure_script_permissions "$ROOT"
  create_desktop_shortcuts "$ROOT" || true
  ts_prog_done
}
