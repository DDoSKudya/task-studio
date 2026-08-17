
TS_FG=$'\033[38;2;255;255;255m'
TS_MUTED=$'\033[38;2;160;160;168m'
TS_VIOLET=$'\033[38;2;179;102;255m'
TS_GOLD=$'\033[38;2;255;215;0m'
TS_DANGER=$'\033[38;2;251;113;133m'
TS_OK=$'\033[38;2;196;160;255m'
TS_BG=$'\033[48;2;5;5;10m'
TS_PANEL=$'\033[48;2;18;18;28m'
TS_SEL_BG=$'\033[48;2;179;102;255m'
TS_SEL_FG=$'\033[38;2;5;5;10m'
TS_SHADOW=$'\033[48;2;0;0;0m'
TS_TITLE_BG=$'\033[48;2;179;102;255m'
TS_TITLE_FG=$'\033[38;2;5;5;10m'
TS_FOOT_BG=$'\033[48;2;12;12;22m'
TS_DIM=$'\033[2m'
TS_BOLD=$'\033[1m'
TS_RESET=$'\033[0m'
TS_HIDE=$'\033[?25l'
TS_SHOW=$'\033[?25h'
TS_ALT_ON=$'\033[?1049h'
TS_ALT_OFF=$'\033[?1049l'
TS_CLEAR=$'\033[2J\033[H'
TS_UI_SPIN_I=0
TS_UI_SPIN_FRAMES='|/-\'
TS_SYNC_BEGIN=$'\033[?2026h'
TS_SYNC_END=$'\033[?2026l'

TS_UI_SESSION=0
TS_UI_SCREEN_READY=0
TS_UI_GEOM=""
TS_UI_PROG_FP=""
TS_UI_MENU_PREV=-1
TS_LAUNCHER_VERSION=""
TS_LAUNCHER_BUILD=""
TS_LAUNCHER_VERSION_LOADED=0

ui_launcher_version_file() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  printf '%s\n' "$here/../launcher-version.json"
}

ui_launcher_load_version() {
  [[ "${TS_LAUNCHER_VERSION_LOADED:-0}" == "1" ]] && return 0
  TS_LAUNCHER_VERSION_LOADED=1
  TS_LAUNCHER_VERSION=""
  TS_LAUNCHER_BUILD=""
  local path
  path="$(ui_launcher_version_file)"
  [[ -f "$path" ]] || return 0
  if command -v python3 >/dev/null 2>&1; then
    local parsed
    parsed="$(
      python3 -c '
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
v=str(d.get("version") or "").strip()
b=d.get("build","")
print(v)
print("" if b is None else str(b).strip())
' "$path" 2>/dev/null || true
    )"
    TS_LAUNCHER_VERSION="$(printf '%s\n' "$parsed" | sed -n '1p')"
    TS_LAUNCHER_BUILD="$(printf '%s\n' "$parsed" | sed -n '2p')"
    return 0
  fi
  TS_LAUNCHER_VERSION="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$path" | head -1)"
  TS_LAUNCHER_BUILD="$(sed -n 's/.*"build"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$path" | head -1)"
}

ui_chrome_app_title() {
  local base="Task Studio Launcher"
  declare -f ts_t >/dev/null 2>&1 && base="$(ts_t app_title)"
  ui_launcher_load_version
  if [[ -n "${TS_LAUNCHER_VERSION:-}" ]]; then
    printf '%s · %s\n' "$base" "$TS_LAUNCHER_VERSION"
  else
    printf '%s\n' "$base"
  fi
}

ui_chrome_footer() {
  local base="$1"
  ui_launcher_load_version
  if [[ -n "${TS_LAUNCHER_BUILD:-}" ]]; then
    printf '%s · build %s\n' "$base" "$TS_LAUNCHER_BUILD"
  else
    printf '%s\n' "$base"
  fi
}

ui_supports_color() {
  { [[ -t 2 ]] || [[ -t 1 ]]; } && [[ "${NO_COLOR:-}" == "" ]] && [[ "${TERM:-}" != "dumb" ]]
}

ui_c() {
  if ui_supports_color; then
    printf '%s' "$1"
  fi
}

ui_log() { printf '%s\n' "$*"; }

ui_info() {
  printf '%s%s%s %s\n' "$(ui_c "$TS_VIOLET")" ">" "$(ui_c "$TS_RESET")" "$*"
}

ui_ok() {
  printf '%s%s%s %s\n' "$(ui_c "$TS_OK")" "+" "$(ui_c "$TS_RESET")" "$*"
}

ui_warn() {
  printf '%s%s%s %s\n' "$(ui_c "$TS_GOLD")" "!" "$(ui_c "$TS_RESET")" "$*"
}

ui_err() {
  printf '%s%s%s %s\n' "$(ui_c "$TS_DANGER")" "x" "$(ui_c "$TS_RESET")" "$*" >&2
}

ui_die() {
  if declare -F ts_prog_active >/dev/null 2>&1 && ts_prog_active; then
    ts_prog_fail "$*" || true
  else
    ui_err "$*"
  fi
  exit 1
}

ui_tty() {
  if [[ -r /dev/tty ]]; then
    printf '%s\n' /dev/tty
  else
    printf '%s\n' /dev/stdin
  fi
}

ui_term_size() {
  local cols rows size
  cols=""
  rows=""
  if [[ -r /dev/tty ]] && size="$(stty size </dev/tty 2>/dev/null)"; then
    rows="${size%% *}"
    cols="${size##* }"
  fi
  if [[ ! "$cols" =~ ^[0-9]+$ ]] || [[ ! "$rows" =~ ^[0-9]+$ ]]; then
    if command -v tput >/dev/null 2>&1; then
      cols="$(tput cols 2>/dev/null || true)"
      rows="$(tput lines 2>/dev/null || true)"
    fi
  fi
  [[ "$cols" =~ ^[0-9]+$ ]] || cols="${COLUMNS:-80}"
  [[ "$rows" =~ ^[0-9]+$ ]] || rows="${LINES:-24}"
  ((cols < 40)) && cols=40
  ((rows < 12)) && rows=12
  printf '%s %s\n' "$cols" "$rows"
}

ui_cols() { ui_term_size | awk '{print $1}'; }
ui_rows() { ui_term_size | awk '{print $2}'; }

ui_pad() {
  local text="$1" width="$2"
  local len=${#text}
  if ((len > width)); then
    if ((width <= 3)); then
      printf '%s' "${text:0:width}"
    else
      printf '%s' "${text:0:$((width - 3))}..."
    fi
    return
  fi
  printf '%s%*s' "$text" "$((width - len))" ""
}

ui_box_size_prefs() {
  local cols rows pref_w pref_h
  read -r cols rows < <(ui_term_size)
  pref_w=$((cols - 4))
  ((pref_w < 56)) && pref_w=56
  pref_h=$((rows - 2))
  ((pref_h < 18)) && pref_h=18
  printf '%s %s\n' "$pref_w" "$pref_h"
}

ui_wrap_text() {
  local text="$1" max_w="$2"
  if [[ -z "$text" ]]; then
    return 0
  fi
  ((max_w < 4)) && max_w=4
  local rest="$text"
  while ((${#rest} > max_w)); do
    local break_at=$max_w
    local chunk="${rest:0:$max_w}"
    if [[ "$chunk" == *" "* ]]; then
      local i=$max_w
      while ((i > 0)) && [[ "${rest:$((i - 1)):1}" != " " ]]; do
        i=$((i - 1))
      done
      if ((i > 0)); then
        break_at=$i
      fi
    fi
    local line="${rest:0:$break_at}"
    line="${line%"${line##*[![:space:]]}"}"
    printf '%s\n' "$line"
    rest="${rest:$break_at}"
    rest="${rest#"${rest%%[![:space:]]*}"}"
  done
  if [[ -n "$rest" ]]; then
    printf '%s\n' "$rest"
  fi
}

ui_wrap_text_limited() {
  local text="$1" max_w="$2" max_lines="$3"
  local -a lines=()
  local line
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -n "$line" ]] && lines+=("$line")
  done < <(ui_wrap_text "$text" "$max_w")
  if ((max_lines > 0 && ${#lines[@]} > max_lines)); then
    local -a trimmed=()
    local i=0
    for ((i = 0; i < max_lines; i++)); do
      trimmed+=("${lines[$i]}")
    done
    lines=("${trimmed[@]}")
    local last_idx=$((max_lines - 1))
    local last="${lines[$last_idx]}"
    if ((${#last} > max_w)); then
      if ((max_w <= 3)); then
        last="${last:0:max_w}"
      else
        last="${last:0:$((max_w - 3))}..."
      fi
      lines[$last_idx]="$last"
    fi
  fi
  printf '%s\n' "${lines[@]}"
}

ui_progress_body_max_lines() {
  local height="$1"
  local max=$((height - 6))
  ((max < 6)) && max=6
  printf '%s\n' "$max"
}

ui_draw_wrapped_in_box() {
  local start_row="$1" left="$2" width="$3" text="$4" style="${5:-normal}" max_lines="${6:-0}"
  local inner=$((width - 4))
  ((inner < 4)) && inner=4
  local -a lines=()
  local line
  if ((max_lines > 0)); then
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -n "$line" ]] && lines+=("$line")
    done < <(ui_wrap_text_limited "$text" "$inner" "$max_lines")
  else
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ -n "$line" ]] && lines+=("$line")
    done < <(ui_wrap_text "$text" "$inner")
  fi
  if ((${#lines[@]} == 0)); then
    lines+=("")
  fi
  local row="$start_row"
  for line in "${lines[@]}"; do
    ui_draw_line_in_box "$row" "$left" "$width" "$line" "$style"
    row=$((row + 1))
  done
  printf '%s\n' "$row"
}

ui_goto() {
  printf '\033[%s;%sH' "$1" "$2" >&2
}

ui_fill() {
  local n="$1" ch="${2:- }"
  local i
  for ((i = 0; i < n; i++)); do
    printf '%s' "$ch"
  done
}

ui_strip_ansi() {
  local s="$1"
  # shellcheck disable=SC2001
  s="$(printf '%s' "$s" | sed -E 's/\x1b\[[0-9;?]*[a-zA-Z]//g; s/\x1b\][^\x07]*\x07//g; s/\r//g')"
  printf '%s' "$s"
}

ui_utf8_ok() {
  [[ "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" == *[Uu][Tt][Ff][-_]*8* ]]
}

ui_sync_begin() {
  printf '%s' "$TS_SYNC_BEGIN" >&2
}

ui_sync_end() {
  printf '%s' "$TS_SYNC_END" >&2
}

ui_paint_screen() {
  local cols rows r force="${1:-}"
  if [[ "$force" != "force" && "$TS_UI_SCREEN_READY" -eq 1 ]]; then
    return 0
  fi
  read -r cols rows < <(ui_term_size)
  ui_sync_begin
  printf '%s%s' "$TS_BG" "$TS_CLEAR" >&2
  for ((r = 1; r <= rows; r++)); do
    ui_goto "$r" 1
    printf '%s' "$TS_BG" >&2
    ui_fill "$cols" " " >&2
  done
  printf '%s' "$TS_RESET" >&2
  ui_sync_end
  TS_UI_SCREEN_READY=1
}

ui_session_start() {
  TS_UI_SESSION=1
  TS_UI_SCREEN_READY=0
  TS_UI_GEOM=""
  TS_UI_PROG_FP=""
  TS_UI_MENU_PREV=-1
  if ! ui_supports_color; then
    return 0
  fi
  printf '%s%s' "$TS_ALT_ON" "$TS_HIDE" >&2
  ui_paint_screen force
}

ui_session_end() {
  TS_UI_SESSION=0
  TS_UI_SCREEN_READY=0
  TS_UI_GEOM=""
  TS_UI_PROG_FP=""
  if ! ui_supports_color; then
    printf '%s' "$TS_SHOW" >&2
    return 0
  fi
  printf '%s%s%s' "$TS_SHOW" "$TS_ALT_OFF" "$TS_RESET" >&2
}

ui_manager_enter() {
  local mode="${1:-}"
  if [[ "$mode" == "force" ]]; then
    TS_UI_SCREEN_READY=0
    TS_UI_GEOM=""
    TS_UI_PROG_FP=""
    TS_UI_MENU_PREV=-1
  fi
  if [[ "$TS_UI_SESSION" -eq 1 ]]; then
    ui_paint_screen "$mode"
    return 0
  fi
  if ! ui_supports_color; then
    return 0
  fi
  printf '%s%s' "$TS_ALT_ON" "$TS_HIDE" >&2
  ui_paint_screen force
}

ui_manager_leave() {
  if [[ "$TS_UI_SESSION" -eq 1 ]]; then
    return 0
  fi
  if ! ui_supports_color; then
    printf '%s' "$TS_SHOW" >&2
    return 0
  fi
  printf '%s%s%s' "$TS_SHOW" "$TS_ALT_OFF" "$TS_RESET" >&2
}

ui_center_box() {
  local pref_w="$1" pref_h="$2"
  local cols rows width height top left
  read -r cols rows < <(ui_term_size)
  width=$pref_w
  height=$pref_h
  ((width > cols - 4)) && width=$((cols - 4))
  ((height > rows - 2)) && height=$((rows - 2))
  ((width < 36)) && width=36
  ((height < 7)) && height=7
  top=$(( (rows - height) / 2 ))
  left=$(( (cols - width) / 2 ))
  ((top < 1)) && top=1
  ((left < 1)) && left=1
  printf '%s %s %s %s\n' "$top" "$left" "$height" "$width"
}

ui_draw_frame() {
  local top="$1" left="$2" height="$3" width="$4" title="$5"
  local footer="${6:-}"
  if [[ -z "$footer" ]]; then
    if declare -f ts_t >/dev/null 2>&1; then footer="$(ts_t menu_footer)"; else footer="↑↓ move · Enter select · q quit"; fi
    footer="$(ui_chrome_footer "$footer")"
  fi
  local chrome="${7:-1}"
  local r inner=$((width - 2))
  local shadow_top=$((top + 1)) shadow_left=$((left + 2))
  local tl tr bl br h v

  if ui_utf8_ok; then
    tl="┌"; tr="┐"; bl="└"; br="┘"; h="─"; v="│"
  else
    tl="+"; tr="+"; bl="+"; br="+"; h="-"; v="|"
  fi

  if [[ "$chrome" == "1" ]]; then
    for ((r = 0; r < height; r++)); do
      ui_goto $((shadow_top + r)) "$shadow_left"
      printf '%s' "$TS_SHADOW" >&2
      ui_fill "$width" " " >&2
      printf '%s' "$TS_RESET" >&2
    done
  fi

  for ((r = 0; r < height; r++)); do
    ui_goto $((top + r)) "$left"
    if ((r == 0)); then
      printf '%s%s' "$TS_TITLE_BG" "$TS_TITLE_FG$TS_BOLD" >&2
      printf '%s' "$(ui_pad "  $title" "$width")" >&2
      printf '%s' "$TS_RESET" >&2
    elif ((r == 1)); then
      printf '%s%s%s' "$TS_PANEL" "$TS_VIOLET" "$tl" >&2
      local i
      for ((i = 0; i < inner; i++)); do printf '%s' "$h" >&2; done
      printf '%s%s' "$tr" "$TS_RESET" >&2
    elif ((r == height - 2)); then
      printf '%s%s%s' "$TS_PANEL" "$TS_VIOLET" "$bl" >&2
      local i
      for ((i = 0; i < inner; i++)); do printf '%s' "$h" >&2; done
      printf '%s%s' "$br" "$TS_RESET" >&2
    elif ((r == height - 1)); then
      printf '%s%s' "$TS_FOOT_BG" "$TS_MUTED" >&2
      printf '%s' "$(ui_pad "  $footer" "$width")" >&2
      printf '%s' "$TS_RESET" >&2
    else
      printf '%s%s%s%s' "$TS_PANEL" "$TS_VIOLET" "$v" "$TS_RESET$TS_PANEL" >&2
      ui_fill "$inner" " " >&2
      printf '%s%s%s' "$TS_VIOLET" "$v" "$TS_RESET" >&2
    fi
  done
}

ui_draw_line_in_box() {
  local row="$1" left="$2" width="$3" text="$4" style="${5:-normal}"
  local inner=$((width - 2))
  local v="|"
  ui_utf8_ok && v="│"
  ui_goto "$row" "$left"
  printf '%s%s%s%s' "$TS_PANEL" "$TS_VIOLET" "$v" "$TS_RESET" >&2
  case "$style" in
    selected)
      printf '%s%s %s %s' "$TS_SEL_BG" "$TS_SEL_FG$TS_BOLD" "$(ui_pad "$text" $((inner - 2)))" "$TS_RESET" >&2
      ;;
    gold)
      printf '%s%s %s %s' "$TS_PANEL" "$TS_GOLD$TS_BOLD" "$(ui_pad "$text" $((inner - 2)))" "$TS_RESET" >&2
      ;;
    muted)
      printf '%s%s %s %s' "$TS_PANEL" "$TS_MUTED" "$(ui_pad "$text" $((inner - 2)))" "$TS_RESET" >&2
      ;;
    ok)
      printf '%s%s %s %s' "$TS_PANEL" "$TS_OK" "$(ui_pad "$text" $((inner - 2)))" "$TS_RESET" >&2
      ;;
    danger)
      printf '%s%s %s %s' "$TS_PANEL" "$TS_DANGER" "$(ui_pad "$text" $((inner - 2)))" "$TS_RESET" >&2
      ;;
    *)
      printf '%s%s %s %s' "$TS_PANEL" "$TS_FG" "$(ui_pad "$text" $((inner - 2)))" "$TS_RESET" >&2
      ;;
  esac
  printf '%s%s%s' "$TS_VIOLET" "$v" "$TS_RESET" >&2
}

ui_banner() { :; }

ui_choose() {
  local prompt="$1"
  shift
  local -a items=("$@")
  local i label value
  local -a labels=() values=()

  for item in "${items[@]}"; do
    if [[ "$item" == *"|"* ]]; then
      value="${item%%|*}"
      label="${item#*|}"
    else
      value="$item"
      label="$item"
    fi
    values+=("$value")
    labels+=("$label")
  done

  if [[ ! -t 0 ]] && [[ ! -r /dev/tty ]]; then
    printf '%s\n' "${values[0]}"
    return 0
  fi

  local tty selected=0 count=${#labels[@]}
  tty="$(ui_tty)"

  local need_h=$((count + 9))
  local pref_w pref_h
  read -r pref_w pref_h < <(ui_box_size_prefs)
  ((pref_h < need_h)) && pref_h=$need_h

  local top left height width geom
  read -r top left height width < <(ui_center_box "$pref_w" "$pref_h")
  geom="$top $left $height $width"

  local list_top=$((top + 4))
  local key key2 key3 seq
  local managed=0
  local need_full=1
  local prev_selected=-1

  if ui_supports_color; then
    managed=1
    ui_manager_enter force
  fi

  printf '%s' "$TS_HIDE" >&2

  while true; do
    if [[ "$managed" -eq 1 ]]; then
      read -r pref_w pref_h < <(ui_box_size_prefs)
      ((pref_h < need_h)) && pref_h=$need_h
      read -r top left height width < <(ui_center_box "$pref_w" "$pref_h")
      list_top=$((top + 4))
      if [[ "$geom" != "$top $left $height $width" ]]; then
        geom="$top $left $height $width"
        need_full=1
        ui_manager_enter force
      fi

      ui_sync_begin
      if [[ "$need_full" -eq 1 ]]; then
        local menu_ft
        if declare -f ts_t >/dev/null 2>&1; then menu_ft="$(ts_t menu_footer)"; else menu_ft="↑↓ move · Enter select · q quit"; fi
        menu_ft="$(ui_chrome_footer "$menu_ft")"
        ui_draw_frame "$top" "$left" "$height" "$width" "$(ui_chrome_app_title)" "$menu_ft" 1
        ui_draw_line_in_box $((top + 2)) "$left" "$width" "$prompt" gold
        ui_draw_line_in_box $((top + 3)) "$left" "$width" "" muted
        for i in "${!labels[@]}"; do
          if [[ "$i" -eq "$selected" ]]; then
            ui_draw_line_in_box $((list_top + i)) "$left" "$width" "> ${labels[$i]}" selected
          else
            ui_draw_line_in_box $((list_top + i)) "$left" "$width" "  ${labels[$i]}" muted
          fi
        done
        need_full=0
        prev_selected=$selected
      elif [[ "$prev_selected" -ne "$selected" ]]; then
        if [[ "$prev_selected" -ge 0 ]]; then
          ui_draw_line_in_box $((list_top + prev_selected)) "$left" "$width" "  ${labels[$prev_selected]}" muted
        fi
        ui_draw_line_in_box $((list_top + selected)) "$left" "$width" "> ${labels[$selected]}" selected
        prev_selected=$selected
      fi
      ui_sync_end
    else
      printf '\n%s\n' "$prompt" >&2
      for i in "${!labels[@]}"; do
        if [[ "$i" -eq "$selected" ]]; then
          printf ' > %s\n' "${labels[$i]}" >&2
        else
          printf '   %s\n' "${labels[$i]}" >&2
        fi
      done
    fi

    IFS= read -r -s -n 1 key <"$tty" || {
      [[ "$managed" -eq 1 ]] && ui_manager_leave
      return 1
    }

    if [[ "$key" == $'\x1b' ]]; then
      key2=""; key3=""
      IFS= read -r -s -n 1 -t 0.05 key2 <"$tty" || true
      if [[ "$key2" == '[' || "$key2" == 'O' ]]; then
        IFS= read -r -s -n 1 -t 0.05 key3 <"$tty" || true
      fi
      seq="${key2}${key3}"
      case "$seq" in
        '[A' | 'OA') selected=$(((selected - 1 + count) % count)) ;;
        '[B' | 'OB') selected=$(((selected + 1) % count)) ;;
      esac
    elif [[ "$key" == 'k' || "$key" == 'K' ]]; then
      selected=$(((selected - 1 + count) % count))
    elif [[ "$key" == 'j' || "$key" == 'J' ]]; then
      selected=$(((selected + 1) % count))
    elif [[ "$key" == 'q' || "$key" == 'Q' ]]; then
      [[ "$managed" -eq 1 ]] && ui_manager_leave
      return 1
    elif [[ -z "$key" || "$key" == $'\n' || "$key" == $'\r' || "$key" == ' ' ]]; then
      [[ "$managed" -eq 1 && "$TS_UI_SESSION" -ne 1 ]] && ui_manager_leave
      printf '%s\n' "${values[$selected]}"
      return 0
    elif [[ "$key" =~ ^[1-9]$ ]]; then
      local idx=$((key - 1))
      if [[ "$idx" -ge 0 && "$idx" -lt "$count" ]]; then
        [[ "$managed" -eq 1 && "$TS_UI_SESSION" -ne 1 ]] && ui_manager_leave
        printf '%s\n' "${values[$idx]}"
        return 0
      fi
    fi
  done
}

ui_confirm() {
  local prompt="${1:-$(ts_t confirm_continue 2>/dev/null || echo Continue?)}"
  local yes_l no_l
  if command -v ts_t >/dev/null 2>&1 || declare -f ts_t >/dev/null 2>&1; then
    yes_l="$(ts_t yes)"
    no_l="$(ts_t no)"
  else
    yes_l="Yes"
    no_l="No"
  fi
  local pick
  pick="$(ui_choose "$prompt" "yes|$yes_l" "no|$no_l")" || return 1
  [[ "$pick" == "yes" ]]
}

ui_confirm_delete() {
  local prompt="${1:-}"
  local del_l can_l
  if [[ -z "$prompt" ]]; then
    if declare -f ts_t >/dev/null 2>&1; then
      prompt="$(ts_t confirm_uninstall)"
    else
      prompt="Delete Task Studio?"
    fi
  fi
  if declare -f ts_t >/dev/null 2>&1; then
    del_l="$(ts_t action_delete)"
    can_l="$(ts_t action_cancel)"
  else
    del_l="Delete"
    can_l="Cancel"
  fi
  local pick
  pick="$(ui_choose "$prompt" "delete|$del_l" "cancel|$can_l")" || return 1
  [[ "$pick" == "delete" ]]
}

ui_confirm_yes() {
  ui_confirm_delete "$@"
}

ui_pause() {
  local message
  if [[ -n "${1:-}" ]]; then
    message="$1"
  elif declare -f ts_t >/dev/null 2>&1; then
    message="$(ts_t press_enter_menu)"
  else
    message="Press Enter to return to the menu..."
  fi
  local tty
  tty="$(ui_tty)"
  if ui_supports_color; then
    local top left height width
    read -r top left height width < <(ui_center_box 56 8)
    ui_manager_enter
    local footer_enter
    if declare -f ts_t >/dev/null 2>&1; then footer_enter="$(ts_t enter_continue)"; else footer_enter="Enter = continue"; fi
    footer_enter="$(ui_chrome_footer "$footer_enter")"
    ui_draw_frame "$top" "$left" "$height" "$width" "$(ui_chrome_app_title)" "$footer_enter"
    ui_draw_line_in_box $((top + 2)) "$left" "$width" "$message" gold
    ui_draw_line_in_box $((top + 3)) "$left" "$width" "" muted
    ui_draw_line_in_box $((top + 4)) "$left" "$width" "[ Enter ]" selected
    printf '%s' "$TS_HIDE" >&2
    local key
    while true; do
      IFS= read -r -s -n 1 key <"$tty" || break
      [[ -z "$key" || "$key" == $'\n' || "$key" == $'\r' || "$key" == ' ' || "$key" == 'q' ]] && break
    done
    ui_manager_leave
  else
    printf '%s' "$message" >&2
    read -r _ <"$tty" || true
  fi
}

ui_progress_bar_string() {
  local pct="$1" width="$2"
  ((width < 8)) && width=8
  local filled=$((pct * width / 100))
  ((filled > width)) && filled=$width
  ((filled < 0)) && filled=0
  local empty=$((width - filled))
  local out="" i
  for ((i = 0; i < filled; i++)); do out+="#"; done
  for ((i = 0; i < empty; i++)); do out+="-"; done
  printf '%s' "$out"
}

ui_spinner_tick() {
  local frames="${TS_UI_SPIN_FRAMES:-|/-\\}"
  frames="${frames//$'\r'/}"
  frames="${frames//$'\n'/}"
  [[ -z "$frames" ]] && frames='|/-\'
  local n=${#frames}
  ((n < 1)) && n=1
  local i=${TS_UI_SPIN_I:-0}
  TS_UI_SPIN_CHAR="${frames:i:1}"
  TS_UI_SPIN_I=$(( (i + 1) % n ))
}

ui_progress_panel_paint() {
  local top="$1" left="$2" height="$3" width="$4"
  local mode="${5:-full}"
  local title group status phase error pct eta_sec bar eta_text pct_text
  local footer fp spin status_line
  local default_title="Task Studio Launcher"
  declare -f ts_t >/dev/null 2>&1 && default_title="$(ts_t app_title)"
  title="$(ts_prog_get title "$default_title")"
  group="$(ts_prog_get group "")"
  status="$(ts_prog_get status "")"
  phase="$(ts_prog_get phase run)"
  error="$(ts_prog_get error "")"
  read -r pct eta_sec < <(ts_prog_compute)
  local chrome_title
  chrome_title="$(ui_chrome_app_title)"
  if [[ "$phase" == "done" ]]; then
    pct=100
    eta_sec=0
    eta_text=""
    spin=""
  elif [[ "$phase" == "error" ]]; then
    eta_text="$(ts_t prog_eta_failed 2>/dev/null || echo failed)"
    spin=""
  else
    ui_spinner_tick
    spin="${TS_UI_SPIN_CHAR}"
    if [[ "$eta_sec" -le 0 ]]; then
      eta_text="$(ts_t prog_eta_finishing 2>/dev/null || echo 'finishing…')"
    else
      if ((eta_sec < 60)); then
        eta_text="$(ts_prog_format_eta $(( (eta_sec / 10) * 10 )))"
      else
        eta_text="$(ts_prog_format_eta $(( (eta_sec / 30) * 30 )))"
      fi
    fi
  fi
  if [[ -n "$spin" ]]; then
    if [[ -n "$status" ]]; then
      status_line="$spin  $status"
    else
      status_line="$spin"
    fi
  else
    status_line="$status"
  fi
  pct_text="${pct}%"
  local bar_w=$((width - 14))
  ((bar_w < 10)) && bar_w=10
  bar="$(ui_progress_bar_string "$pct" "$bar_w")"

  footer="$(ts_t prog_footer_idle 2>/dev/null || echo 'progress / Enter when done')"
  [[ "$phase" == "run" ]] && footer="$(ts_t prog_footer_run 2>/dev/null || echo 'working… please wait')"
  [[ "$phase" == "error" || "$phase" == "done" ]] && footer="${TS_UI_RETURN_FOOTER:-$(ts_t prog_footer_return 2>/dev/null || echo 'Enter = back / auto in 5s')}"
  footer="$(ui_chrome_footer "$footer")"

  local log_hint
  if [[ "$phase" == "error" ]]; then
    log_hint="$(ts_t prog_log_hint "${TS_PROGRESS_LOG:-data/logs/studio-last.log}" 2>/dev/null || echo "Full log: ${TS_PROGRESS_LOG:-data/logs/studio-last.log}")"
  else
    log_hint="$(ts_t prog_details "${TS_PROGRESS_LOG:-data/logs/studio-last.log}" 2>/dev/null || echo "Log: ${TS_PROGRESS_LOG:-data/logs/studio-last.log}")"
  fi

  local body_max
  body_max="$(ui_progress_body_max_lines "$height")"
  local status_max=3
  local log_max=2
  if ((body_max < 12)); then
    status_max=2
    log_max=1
  fi

  local frame_title="$chrome_title"
  if [[ -n "$title" && "$title" != "$default_title" ]]; then
    frame_title="$chrome_title · $title"
  fi

  fp="${title}|${group}|${status_line}|${phase}|${error}|${pct}|${eta_text}|${footer}|${spin}|${log_hint}"
  if [[ "$mode" == "update" && "$fp" == "${TS_UI_PROG_FP:-}" ]]; then
    return 0
  fi
  TS_UI_PROG_FP="$fp"

  ui_sync_begin
  if [[ "$mode" == "full" ]]; then
    ui_draw_frame "$top" "$left" "$height" "$width" "$frame_title" "$footer" 1
  else
    ui_goto "$top" "$left"
    printf '%s%s' "$TS_TITLE_BG" "$TS_TITLE_FG$TS_BOLD" >&2
    printf '%s' "$(ui_pad "  $frame_title" "$width")" >&2
    printf '%s' "$TS_RESET" >&2
    ui_goto $((top + height - 1)) "$left"
    printf '%s%s' "$TS_FOOT_BG" "$TS_MUTED" >&2
    printf '%s' "$(ui_pad "  $footer" "$width")" >&2
    printf '%s' "$TS_RESET" >&2
  fi

  local body_row=$((top + 2))
  ui_draw_line_in_box "$body_row" "$left" "$width" "" muted
  body_row=$((body_row + 1))
  ui_draw_line_in_box "$body_row" "$left" "$width" "$group" gold
  body_row=$((body_row + 1))
  body_row="$(ui_draw_wrapped_in_box "$body_row" "$left" "$width" "$status_line" muted "$status_max")"
  ui_draw_line_in_box "$body_row" "$left" "$width" "" muted
  body_row=$((body_row + 1))
  ui_draw_line_in_box "$body_row" "$left" "$width" "[${bar}] ${pct_text}" selected
  body_row=$((body_row + 1))
  ui_draw_line_in_box "$body_row" "$left" "$width" "$eta_text" muted
  body_row=$((body_row + 1))
  ui_draw_line_in_box "$body_row" "$left" "$width" "" muted
  body_row=$((body_row + 1))

  if [[ "$phase" == "error" ]]; then
    ui_draw_line_in_box "$body_row" "$left" "$width" "$(ts_t prog_error_label 2>/dev/null || echo Error)" danger
    body_row=$((body_row + 1))
    local -a excerpt_lines=()
    local eline
    while IFS= read -r eline || [[ -n "$eline" ]]; do
      [[ -n "$eline" ]] && excerpt_lines+=("$eline")
    done < <(ts_prog_error_excerpt "${TS_PROGRESS_LOG:-}" 5 2>/dev/null || true)
    if ((${#excerpt_lines[@]} == 0)); then
      excerpt_lines=("${error:-$(ts_t prog_unknown_error 2>/dev/null || echo 'Unknown error')}")
    fi
    local ei=0 excerpt_max=3
    ((body_max < 12)) && excerpt_max=2
    for eline in "${excerpt_lines[@]}"; do
      ((ei >= excerpt_max)) && break
      body_row="$(ui_draw_wrapped_in_box "$body_row" "$left" "$width" "$eline" danger 2)"
      ei=$((ei + 1))
    done
    body_row="$(ui_draw_wrapped_in_box "$body_row" "$left" "$width" "$log_hint" muted "$log_max")"
  elif [[ "$phase" == "done" ]]; then
    ui_draw_line_in_box "$body_row" "$left" "$width" "$(ts_t prog_completed 2>/dev/null || echo 'Completed successfully')" ok
    body_row=$((body_row + 1))
    body_row="$(ui_draw_wrapped_in_box "$body_row" "$left" "$width" "$log_hint" muted "$log_max")"
  else
    body_row="$(ui_draw_wrapped_in_box "$body_row" "$left" "$width" "$log_hint" muted "$log_max")"
  fi

  while ((body_row < top + height - 2)); do
    ui_draw_line_in_box "$body_row" "$left" "$width" "" muted
    body_row=$((body_row + 1))
  done
  ui_sync_end
}

ui_run_progress() {
  local title="$1"
  shift
  local tty top left height width cols rows pref_w pref_h geom
  tty="$(ui_tty)"

  export TS_PROGRESS_FILE
  export TS_PROGRESS_LOG
  TS_PROGRESS_FILE="$(mktemp "${TMPDIR:-/tmp}/ts-prog.XXXXXX")"
  if [[ -z "${ROOT:-}" ]]; then
    ops_find_root_quiet 2>/dev/null || true
  fi
  TS_PROGRESS_LOG="$(ts_progress_log_path "${ROOT:-$(pwd -P 2>/dev/null || pwd)}")"
  : >"$TS_PROGRESS_FILE"
  if ! : >"$TS_PROGRESS_LOG" 2>/dev/null; then
    TS_PROGRESS_LOG="$(mktemp "${TMPDIR:-/tmp}/ts-studio.XXXXXX.log")"
    : >"$TS_PROGRESS_LOG"
  fi
  TS_UI_PROG_FP=""
  ts_prog_write "title=$title" "phase=run" "group=$title" "status=" "pct_lo=0" "pct_hi=5" \
    "stage_t0=$(date +%s)" "stage_est=10" "stages_left_est=0" "error=" "pct=0"

  read -r pref_w pref_h < <(ui_box_size_prefs)
  read -r top left height width < <(ui_center_box "$pref_w" "$pref_h")
  geom="$top $left $height $width"

  if ui_supports_color; then
    ui_manager_enter force
    ui_progress_panel_paint "$top" "$left" "$height" "$width" full
  else
    printf '\n=== %s ===\n' "$title" >&2
    printf '%s\n' "$(ts_t prog_details "$TS_PROGRESS_LOG" 2>/dev/null || echo "Log: $TS_PROGRESS_LOG")" >&2
  fi

  set +e
  if ! : >>"$TS_PROGRESS_LOG" 2>/dev/null; then
    TS_PROGRESS_LOG="$(mktemp "${TMPDIR:-/tmp}/ts-studio.XXXXXX.log")"
  fi
  (
    "$@"
  ) >"$TS_PROGRESS_LOG" 2>&1 &
  local pid=$!
  local rc=0

  if ui_supports_color; then
    while kill -0 "$pid" 2>/dev/null; do
      read -r pref_w pref_h < <(ui_box_size_prefs)
      read -r top left height width < <(ui_center_box "$pref_w" "$pref_h")
      if [[ "$geom" != "$top $left $height $width" ]]; then
        geom="$top $left $height $width"
        TS_UI_PROG_FP=""
        ui_manager_enter force
        ui_progress_panel_paint "$top" "$left" "$height" "$width" full
      else
        ui_progress_panel_paint "$top" "$left" "$height" "$width" update
      fi
      sleep 0.35
    done
    wait "$pid"
    rc=$?
    if [[ "$rc" -ne 0 ]]; then
      local err
      err="$(ts_prog_get error "")"
      if [[ -z "$err" ]]; then
        err="$(ts_prog_extract_error "$TS_PROGRESS_LOG" || true)"
      fi
      if [[ -z "$err" ]]; then
        if [[ ! -s "$TS_PROGRESS_LOG" ]]; then
          err="$(ts_t err_progress_empty_log "$TS_PROGRESS_LOG" 2>/dev/null || echo "Command failed before writing a log (exit $rc). Check Docker and permissions on data/.")"
        else
          err="$(ts_t cmd_failed "$rc" 2>/dev/null || echo "Command failed (exit $rc)")"
        fi
      fi
      ts_prog_write "phase=error" "error=$err" "status=$(ts_t prog_failed 2>/dev/null || echo Failed)"
    else
      local phase
      phase="$(ts_prog_get phase run)"
      if [[ "$phase" != "done" && "$phase" != "error" ]]; then
        ts_prog_done
      fi
    fi
    TS_UI_PROG_FP=""
    ui_progress_panel_paint "$top" "$left" "$height" "$width" update
    local left_sec=5 key
    while ((left_sec > 0)); do
      TS_UI_RETURN_FOOTER="$(ts_t returning_footer "$left_sec" 2>/dev/null || echo "Returning in ${left_sec}s / Enter = now")"
      TS_UI_PROG_FP=""
      ui_progress_panel_paint "$top" "$left" "$height" "$width" update
      key=""
      IFS= read -r -s -n 1 -t 1 key <"$tty" || true
      if [[ -n "$key" ]]; then
        [[ "$key" == $'\n' || "$key" == $'\r' || "$key" == ' ' || "$key" == 'q' || "$key" == 'Q' ]] && break
        break
      fi
      left_sec=$((left_sec - 1))
    done
    unset TS_UI_RETURN_FOOTER
  else
    while kill -0 "$pid" 2>/dev/null; do
      printf '\r%s: %s (%s%%)   ' "$title" "$(ts_prog_get group …)" "$(ts_prog_compute | awk '{print $1}')" >&2
      sleep 1
    done
    wait "$pid"
    rc=$?
    printf '\n' >&2
    if [[ "$rc" -ne 0 ]]; then
      ts_prog_extract_error "$TS_PROGRESS_LOG" >&2 || true
      printf '%s\n' "$(ts_t prog_log_hint "$TS_PROGRESS_LOG" 2>/dev/null || echo "Full log: $TS_PROGRESS_LOG")" >&2
      printf '\n--- log excerpt ---\n' >&2
      ts_prog_error_excerpt "$TS_PROGRESS_LOG" 8 >&2 || true
      printf '---\n' >&2
      sleep 5
    else
      printf '%s\n' "$(ts_t done_returning 2>/dev/null || echo 'Done. Returning in 5s…')" >&2
      sleep 5
    fi
  fi

  set -e
  local prog_file="$TS_PROGRESS_FILE"
  unset TS_PROGRESS_FILE
  rm -f "$prog_file" 2>/dev/null || true
  return "$rc"
}

ui_run_logged() {
  ui_run_progress "$@"
}

ui_show_text() {
  local title="$1"
  shift
  local -a lines=("$@")
  local tty top left height width pref_w pref_h
  tty="$(ui_tty)"
  read -r pref_w pref_h < <(ui_box_size_prefs)
  pref_h=$((${#lines[@]} + 8))
  read -r top left height width < <(ui_center_box "$pref_w" "$pref_h")

  if ui_supports_color; then
    ui_manager_enter
    ui_paint_screen
    local enter_back="Enter = back"
    declare -f ts_t >/dev/null 2>&1 && enter_back="$(ts_t enter_back)"
    enter_back="$(ui_chrome_footer "$enter_back")"
    ui_draw_frame "$top" "$left" "$height" "$width" "$title" "$enter_back"
    local i
    for i in "${!lines[@]}"; do
      ui_draw_line_in_box $((top + 2 + i)) "$left" "$width" "${lines[$i]}" muted
    done
    ui_draw_line_in_box $((top + height - 3)) "$left" "$width" "[ Enter ]" selected
    local key
    while true; do
      IFS= read -r -s -n 1 key <"$tty" || break
      [[ -z "$key" || "$key" == $'\n' || "$key" == $'\r' || "$key" == ' ' || "$key" == 'q' ]] && break
    done
  else
    printf '\n%s\n' "$title" >&2
    local line
    for line in "${lines[@]}"; do
      printf '  %s\n' "$line" >&2
    done
    read -r _ <"$tty" || true
  fi
}
