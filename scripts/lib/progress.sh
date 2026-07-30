# Progress state for the dialog manager (stages, %, ETA, errors).
# Used when TS_PROGRESS_FILE is set by ui_run_progress.
# Format of the state file: key=value lines (no spaces around =).

TS_PROG_IDS=()
TS_PROG_LABELS=()
TS_PROG_EST=()
TS_PROG_INDEX=-1

ts_prog_active() {
  [[ -n "${TS_PROGRESS_FILE:-}" ]]
}

ts_prog_now() {
  date +%s
}

ts_prog_write() {
  # Append key=value lines; readers take the last value per key.
  ts_prog_active || return 0
  local line
  for line in "$@"; do
    printf '%s\n' "$line" >>"$TS_PROGRESS_FILE"
  done
}

ts_prog_get() {
  local key="$1" def="${2:-}"
  ts_prog_active || { printf '%s\n' "$def"; return; }
  local line
  line="$(grep -E "^${key}=" "$TS_PROGRESS_FILE" 2>/dev/null | tail -1 || true)"
  if [[ -z "$line" ]]; then
    printf '%s\n' "$def"
  else
    printf '%s\n' "${line#*=}"
  fi
}

# Begin a run. Optional title (also set by ui_run_progress).
ts_prog_begin() {
  local title="${1:-}"
  if [[ -z "$title" ]]; then
    if declare -f ts_t >/dev/null 2>&1; then
      title="$(ts_t app_title)"
    else
      title="Task Studio Launcher"
    fi
  fi
  TS_PROG_IDS=()
  TS_PROG_LABELS=()
  TS_PROG_EST=()
  TS_PROG_INDEX=-1
  if ts_prog_active; then
    ts_prog_write \
      "title=$title" \
      "group=$(ts_t prog_starting 2>/dev/null || echo Starting)" \
      "status=" \
      "pct_lo=0" \
      "pct_hi=2" \
      "stage_t0=$(ts_prog_now)" \
      "stage_est=5" \
      "stages_left_est=0" \
      "error=" \
      "phase=run" \
      "pct=0"
  else
    ui_info "$title"
  fi
}

# Register plan: each arg is id|Label|est_seconds
ts_prog_plan() {
  local item id label est
  TS_PROG_IDS=()
  TS_PROG_LABELS=()
  TS_PROG_EST=()
  for item in "$@"; do
    id="${item%%|*}"
    local rest="${item#*|}"
    label="${rest%%|*}"
    est="${rest##*|}"
    [[ "$est" =~ ^[0-9]+$ ]] || est=60
    TS_PROG_IDS+=("$id")
    TS_PROG_LABELS+=("$label")
    TS_PROG_EST+=("$est")
  done
  local total=0 e
  for e in "${TS_PROG_EST[@]}"; do
    total=$((total + e))
  done
  ts_prog_write "plan_total_est=$total"
}

ts_prog_sum_from() {
  local from="$1" sum=0 i
  for ((i = from; i < ${#TS_PROG_EST[@]}; i++)); do
    sum=$((sum + TS_PROG_EST[i]))
  done
  printf '%s\n' "$sum"
}

ts_prog_weight_before() {
  local idx="$1" sum=0 i
  for ((i = 0; i < idx; i++)); do
    sum=$((sum + TS_PROG_EST[i]))
  done
  printf '%s\n' "$sum"
}

# Enter stage by id (must be in plan).
ts_prog_enter() {
  local id="$1"
  local status="${2:-}"
  local i idx=-1
  for i in "${!TS_PROG_IDS[@]}"; do
    if [[ "${TS_PROG_IDS[$i]}" == "$id" ]]; then
      idx=$i
      break
    fi
  done
  if [[ "$idx" -lt 0 ]]; then
    ts_prog_status "${status:-$id}"
    return 0
  fi
  TS_PROG_INDEX=$idx
  local total before after left label est pct_lo pct_hi
  total=0
  for i in "${TS_PROG_EST[@]}"; do total=$((total + i)); done
  ((total < 1)) && total=1
  before="$(ts_prog_weight_before "$idx")"
  est="${TS_PROG_EST[$idx]}"
  after=$((before + est))
  left="$(ts_prog_sum_from $((idx + 1)))"
  label="${TS_PROG_LABELS[$idx]}"
  pct_lo=$((before * 100 / total))
  pct_hi=$((after * 100 / total))
  ((pct_hi > 99)) && pct_hi=99
  if ! ts_prog_active; then
    ui_info "[$label] ${status:-…}"
    return 0
  fi
  ts_prog_write \
    "group=$label" \
    "status=${status:-}" \
    "pct_lo=$pct_lo" \
    "pct_hi=$pct_hi" \
    "stage_t0=$(ts_prog_now)" \
    "stage_est=$est" \
    "stages_left_est=$left" \
    "pct=$pct_lo" \
    "error=" \
    "phase=run"
}

ts_prog_status() {
  local msg="$1"
  if ts_prog_active; then
    ts_prog_write "status=$msg"
  else
    ui_info "$msg"
  fi
}

ts_prog_fail() {
  local msg="$1"
  # Keep message to one line for the panel
  msg="${msg//$'\n'/ }"
  msg="${msg:0:200}"
  if ts_prog_active; then
    ts_prog_write "phase=error" "error=$msg" "status=$(ts_t prog_failed 2>/dev/null || echo Failed)"
  fi
  # Outside an active progress session, callers (ui_die) print the error once.
}

ts_prog_done() {
  if ts_prog_active; then
    ts_prog_write \
      "phase=done" \
      "pct=100" \
      "pct_lo=100" \
      "pct_hi=100" \
      "group=$(ts_t prog_done 2>/dev/null || echo Done)" \
      "status=$(ts_t prog_finished_ok 2>/dev/null || echo 'Finished successfully')" \
      "stages_left_est=0" \
      "stage_est=0" \
      "error="
  else
    ui_ok "$(ts_t prog_done 2>/dev/null || echo Done)."
  fi
}

# Compute display pct + eta from state (for the painter).
# Prints: pct eta_sec
ts_prog_compute() {
  local pct_lo pct_hi stage_t0 stage_est left now elapsed frac pct remain
  pct_lo="$(ts_prog_get pct_lo 0)"
  pct_hi="$(ts_prog_get pct_hi 1)"
  stage_t0="$(ts_prog_get stage_t0 "$(ts_prog_now)")"
  stage_est="$(ts_prog_get stage_est 60)"
  left="$(ts_prog_get stages_left_est 0)"
  now="$(ts_prog_now)"
  elapsed=$((now - stage_t0))
  ((elapsed < 0)) && elapsed=0
  ((stage_est < 1)) && stage_est=1
  # Soft fill inside the stage, never quite reach pct_hi until stage ends
  if ((elapsed * 100 / stage_est > 92)); then
    frac=92
  else
    frac=$((elapsed * 100 / stage_est))
  fi
  pct=$((pct_lo + (pct_hi - pct_lo) * frac / 100))
  ((pct > 99)) && pct=99
  remain=$((stage_est - elapsed))
  ((remain < 0)) && remain=0
  remain=$((remain + left))
  printf '%s %s\n' "$pct" "$remain"
}

ts_prog_format_eta() {
  local sec="$1"
  if declare -f ts_t >/dev/null 2>&1; then
    if ((sec < 60)); then
      ts_t prog_eta_sec "$sec"
    elif ((sec < 3600)); then
      ts_t prog_eta_min "$(( (sec + 30) / 60 ))"
    else
      ts_t prog_eta_hm "$((sec / 3600))" "$(( (sec % 3600) / 60 ))"
    fi
    return
  fi
  if ((sec < 60)); then
    printf '~ %ss left' "$sec"
  elif ((sec < 3600)); then
    printf '~ %s min left' "$(( (sec + 30) / 60 ))"
  else
    printf '~ %sh %sm left' "$((sec / 3600))" "$(( (sec % 3600) / 60 ))"
  fi
}

# Extract a useful error line from the log file.
ts_prog_extract_error() {
  local log="${1:-${TS_PROGRESS_LOG:-}}"
  [[ -n "$log" && -f "$log" ]] || return 1
  local line
  line="$(
    grep -iE 'error:|fatal:|failed|denied|cannot |no such|not found|permission|refused|timeout' "$log" 2>/dev/null \
      | grep -viE 'deprecated|warning:' \
      | tail -1 \
      || true
  )"
  if [[ -z "$line" ]]; then
    line="$(tail -n 5 "$log" 2>/dev/null | head -1 || true)"
  fi
  line="$(ui_strip_ansi "$line" 2>/dev/null || printf '%s' "$line")"
  line="${line:0:180}"
  [[ -n "$line" ]] || return 1
  printf '%s\n' "$line"
}
