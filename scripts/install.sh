#!/usr/bin/env bash
set -euo pipefail

REPO_SSH="${TASK_STUDIO_REPO_SSH:-git@github.com:DDoSKudya/task-studio.git}"
REPO_HTTPS="${TASK_STUDIO_REPO_HTTPS:-https://github.com/DDoSKudya/task-studio.git}"
REPO_BRANCH="${TASK_STUDIO_BRANCH:-develop}"
INSTALL_DIR="${TASK_STUDIO_DIR:-$HOME/task-studio}"
COMPOSE_FILE="deploy/docker-compose.yml"
MIN_RAM_GB="${TASK_STUDIO_MIN_RAM_GB:-8}"
OLLAMA_MODEL_DEFAULT="${OLLAMA_MODEL:-qwen2.5:3b}"

log() { printf '%s\n' "$*"; }
die() { printf 'Ошибка: %s\n' "$*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Не найдена команда «$1». Установите Docker Desktop (или Docker Engine + Compose v2) и повторите."
}

detect_ram_gb() {
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

ensure_repo() {
  if [[ -f "$COMPOSE_FILE" && -f ".env.example" ]]; then
    ROOT="$(pwd -P)"
    return
  fi
  if [[ -f "$INSTALL_DIR/$COMPOSE_FILE" ]]; then
    cd "$INSTALL_DIR"
    ROOT="$(pwd -P)"
    return
  fi
  log "Репозиторий не найден — клонирую в $INSTALL_DIR …"
  need_cmd git
  mkdir -p "$(dirname "$INSTALL_DIR")"
  if git clone --branch "$REPO_BRANCH" --depth 1 "$REPO_HTTPS" "$INSTALL_DIR" 2>/dev/null; then
    :
  else
    git clone --branch "$REPO_BRANCH" --depth 1 "$REPO_SSH" "$INSTALL_DIR"
  fi
  cd "$INSTALL_DIR"
  ROOT="$(pwd -P)"
}

ensure_env() {
  if [[ ! -f .env ]]; then
    cp .env.example .env
    log "Создан файл .env из .env.example"
  fi

  local key jwt gid cur

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
    need_cmd openssl
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
    log "Сгенерирован SECRETS_MASTER_KEY"
  fi

  if [[ -n "${jwt:-}" ]]; then
    if grep -q '^JWT_SECRET=' .env; then
      sed -i.bak "s|^JWT_SECRET=.*|JWT_SECRET=$jwt|" .env
    else
      printf '\nJWT_SECRET=%s\n' "$jwt" >> .env
    fi
    rm -f .env.bak
    log "Сгенерирован JWT_SECRET"
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

prepare_dirs() {
  mkdir -p \
    data/postgres data/redis data/rabbitmq data/packs \
    data/meilisearch data/clickhouse data/minio data/ollama \
    data/grafana data/prometheus data/piston/packages
  chmod -R a+rwX data/packs 2>/dev/null || true
}

compose_cmd() {
  docker compose -f "$COMPOSE_FILE" --env-file .env "$@"
}

profiles_args() {
  local mode="${ORCHESTRATOR_MODE:-balancing}"
  local args=(--profile full)
  if [[ "$mode" != "power_saving" ]]; then
    args+=(--profile editor)
  fi
  printf '%s\n' "${args[@]}"
}

wait_http() {
  local url="${1:-http://127.0.0.1}"
  local tries="${2:-90}"
  local i
  for ((i = 1; i <= tries; i++)); do
    if curl -fsS -o /dev/null --max-time 3 "$url" 2>/dev/null; then
      return 0
    fi
    sleep 5
  done
  return 1
}

pull_ollama_model() {
  local model
  model="$(grep -E '^OLLAMA_MODEL=' .env | head -1 | cut -d= -f2- | tr -d '[:space:]')"
  model="${model:-$OLLAMA_MODEL_DEFAULT}"
  log "Загружаю модель Ollama: $model (может занять время)…"
  compose_cmd --profile full exec -T ollama ollama pull "$model" || log "Предупреждение: не удалось скачать модель сейчас. Позже: docker compose -f $COMPOSE_FILE --env-file .env --profile full exec ollama ollama pull $model"
}

main() {
  export DOCKER_BUILDKIT=1
  export COMPOSE_DOCKER_CLI_BUILD=1

  need_cmd docker
  docker info >/dev/null 2>&1 || die "Docker не запущен. Откройте Docker Desktop и дождитесь готовности."
  docker compose version >/dev/null 2>&1 || die "Нужен Docker Compose v2 (команда: docker compose)."

  local ram
  ram="$(detect_ram_gb)"
  if [[ "$ram" -gt 0 && "$ram" -lt "$MIN_RAM_GB" ]]; then
    die "Обнаружено ≈${ram} ГБ RAM, минимум для запуска — ${MIN_RAM_GB} ГБ (рекомендуется 16 ГБ)."
  fi
  if [[ "$ram" -gt 0 && "$ram" -lt 16 ]]; then
    export ORCHESTRATOR_MODE="${ORCHESTRATOR_MODE:-power_saving}"
    log "RAM ≈${ram} ГБ — режим ORCHESTRATOR_MODE=power_saving (без профиля editor)."
  fi

  ensure_repo
  cd "$ROOT"
  ensure_env
  prepare_dirs

  local profile_args
  profile_args="$(profiles_args | tr '\n' ' ')"
  # shellcheck disable=SC2086
  log "Собираю и запускаю контейнеры (первый запуск долгий)…"
  # shellcheck disable=SC2086
  compose_cmd $profile_args build
  # shellcheck disable=SC2086
  compose_cmd $profile_args up -d --remove-orphans

  log "Жду готовности http://localhost …"
  if wait_http "http://127.0.0.1" 90; then
    log "Стек отвечает на http://localhost"
  else
    log "Предупреждение: http://localhost пока не отвечает. Проверьте: docker compose -f $COMPOSE_FILE --env-file .env ps"
  fi

  pull_ollama_model

  log ""
  log "Готово."
  log "  Каталог:  $ROOT"
  log "  UI:        http://localhost"
  log "  Остановка: ./scripts/stop.sh"
  log "  Зарегистрируйте пользователя на странице входа."
}

main "$@"
