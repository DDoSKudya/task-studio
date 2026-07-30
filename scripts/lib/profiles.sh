# Shared compose profiles for install/start (source from repo scripts).
# Expects COMPOSE_FILE already set; cwd = repo root.

is_docker_desktop() {
  docker info --format '{{.OperatingSystem}} {{.Name}}' 2>/dev/null | grep -qi 'docker desktop'
}

# node-exporter/cadvisor mount host / with rslave — breaks Docker Desktop.
can_use_host_metrics() {
  [[ "$(uname -s)" == "Linux" ]] || return 1
  is_docker_desktop && return 1
  return 0
}

profiles_args() {
  local mode="${ORCHESTRATOR_MODE:-balancing}"
  local args=(--profile full)
  if [[ "$mode" != "power_saving" ]]; then
    args+=(--profile editor)
  fi
  if can_use_host_metrics; then
    args+=(--profile host-metrics)
  fi
  printf '%s\n' "${args[@]}"
}

resolve_repo_root() {
  local compose="${COMPOSE_FILE:-deploy/docker-compose.yml}"
  if [[ -f "$compose" && -f .env ]]; then
    pwd -P
    return 0
  fi
  if [[ -f "$HOME/task-studio/$compose" && -f "$HOME/task-studio/.env" ]]; then
    cd "$HOME/task-studio"
    pwd -P
    return 0
  fi
  return 1
}
