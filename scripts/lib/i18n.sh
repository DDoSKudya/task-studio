# Locale for Task Studio Launcher (sourced by studio.sh, ops, ui).
# Russian OS → Cyrillic UI; everything else → English. No user switches.

TS_UI_LANG="${TS_UI_LANG:-}"

ts_detect_lang() {
  local loc=""
  loc="${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}"
  if [[ -z "$loc" || "$loc" == "C" || "$loc" == "POSIX" ]]; then
    if [[ "$(uname -s 2>/dev/null || true)" == "Darwin" ]] && command -v defaults >/dev/null 2>&1; then
      loc="$(defaults read -g AppleLocale 2>/dev/null || true)"
    fi
  fi
  # Normalize: ru_RU.UTF-8 → ru_ru.utf-8
  loc="$(printf '%s' "$loc" | tr '[:upper:]' '[:lower:]')"
  case "$loc" in
    ru|ru_*|ru.*|*.ru|ru@*|*"ru_ru"*)
      TS_UI_LANG=ru
      ;;
    *)
      TS_UI_LANG=en
      ;;
  esac
  export TS_UI_LANG
}

# Usage: ts_t key   or   ts_t key arg1 arg2…  (printf-style in the template)
ts_t() {
  local key="${1:-}"
  shift || true
  local en="" ru="" text=""
  case "$key" in
    yes) en="Yes"; ru="Да" ;;
    no) en="No"; ru="Нет" ;;
    action_delete) en="Delete"; ru="Удалить" ;;
    action_cancel) en="Cancel"; ru="Отмена" ;;
    app_title) en="Task Studio Launcher"; ru="Task Studio Launcher" ;;
    enter_back) en="Enter = back"; ru="Enter — назад" ;;
    press_enter_close) en="Press Enter to close…"; ru="Нажмите Enter, чтобы закрыть…" ;;
    shortcut_fail_exit) en="Task Studio Launcher failed with exit code %s."; ru="Task Studio Launcher завершился с кодом %s." ;;
    shortcut_blocked_hint) en="If the script is blocked, run from Terminal:"; ru="Если скрипт заблокирован, запустите из Terminal:" ;;
    warn_desktop_unwritable) en="Cannot write to desktop directory: %s"; ru="Нельзя писать в папку рабочего стола: %s" ;;
    shortcuts_created) en="Shortcuts: %s"; ru="Ярлыки: %s" ;;
    cmd_failed_short) en="Command failed"; ru="Команда завершилась с ошибкой" ;;
    status_creating_shortcuts) en="Creating desktop shortcuts"; ru="Создание ярлыков на рабочем столе" ;;
    status_checking_ui_plain) en="Checking UI"; ru="Проверка UI" ;;
    warn_purge_skip_got) en="-Purge skipped — path is not %s (got %s)."; ru="-Purge пропущен — путь не %s (сейчас %s)." ;;
    warn_refresh_shortcuts) en="Could not refresh shortcuts — %s"; ru="Не удалось обновить ярлыки — %s" ;;
    err_build_short) en="Docker build failed."; ru="Сборка Docker не удалась." ;;
    err_robocopy_code) en="robocopy failed with code %s"; ru="robocopy завершился с кодом %s" ;;
    type_yes_continue) en="Type YES to continue:"; ru="Введите YES для продолжения:" ;;
    type_yes_hint) en="Type YES (uppercase) to confirm. Anything else cancels."; ru="Введите YES (заглавными), чтобы подтвердить. Любой другой ввод — отмена." ;;
    confirm_continue) en="Continue?"; ru="Продолжить?" ;;
    press_enter_menu) en="Press Enter to return to the menu..."; ru="Нажмите Enter, чтобы вернуться в меню…" ;;
    enter_continue) en="Enter = continue"; ru="Enter = дальше" ;;
    returning_footer) en="Returning in %ss / Enter = now"; ru="Возврат через %s с / Enter = сразу" ;;
    menu_footer) en="arrows move / Enter select / q quit"; ru="стрелки — выбор / Enter — ок / q — выход" ;;
    menu_footer_ps) en="arrows move / Enter select / Esc quit"; ru="стрелки — выбор / Enter — ок / Esc — выход" ;;
    prog_footer_idle) en="progress / Enter when done"; ru="прогресс / Enter — когда готово" ;;
    prog_footer_run) en="working… please wait"; ru="работаю… подождите" ;;
    prog_footer_return) en="Enter = back / auto in 5s"; ru="Enter — назад / авто через 5 с" ;;
    prog_details) en="Log: %s"; ru="Лог: %s" ;;
    prog_details_ps) en="Log: %s"; ru="Лог: %s" ;;
    prog_log_hint) en="Full log: %s"; ru="Полный лог: %s" ;;
    prog_eta_sec) en="~ %ss left"; ru="~ %s с осталось" ;;
    prog_eta_min) en="~ %s min left"; ru="~ %s мин осталось" ;;
    prog_eta_hm) en="~ %sh %sm left"; ru="~ %s ч %s мин осталось" ;;
    prog_eta_failed) en="failed"; ru="ошибка" ;;
    prog_eta_finishing) en="finishing…"; ru="завершение…" ;;
    prog_eta_done) en="done"; ru="готово" ;;
    prog_spinner_frames) en="|/-\\"; ru="|/-\\" ;;
    prog_error_label) en="Error"; ru="Ошибка" ;;
    prog_unknown_error) en="Unknown error"; ru="Неизвестная ошибка" ;;
    prog_completed) en="Completed successfully"; ru="Успешно завершено" ;;
    done_returning) en="Done. Returning in 5s…"; ru="Готово. Возврат через 5 с…" ;;
    prog_starting) en="Starting"; ru="Старт" ;;
    prog_done) en="Done"; ru="Готово" ;;
    prog_failed) en="Failed"; ru="Ошибка" ;;
    prog_finished_ok) en="Finished successfully"; ru="Успешно завершено" ;;
    cmd_failed) en="Command failed (exit %s)"; ru="Команда завершилась с ошибкой (код %s)" ;;
    err_progress_empty_log) en="Command failed before writing a log (exit early). Often data/logs is not writable (Docker owns data/). Log path: %s"; ru="Команда упала до записи лога. Часто data/logs недоступен для записи (каталог data/ создал Docker). Путь лога: %s" ;;

    # menu
    menu_install) en="Install - first-time setup"; ru="Установка — первый запуск" ;;
    menu_start) en="Start - run app and open browser"; ru="Старт — запуск и открытие браузера" ;;
    menu_heal) en="Heal - start missing / stopped containers"; ru="Починить — поднять недостающие и остановленные" ;;
    menu_open) en="Open - launch web UI in browser"; ru="Открыть — web-интерфейс в браузере" ;;
    menu_install_repair) en="Install / repair - rebuild stack"; ru="Установка / ремонт — пересборка стека" ;;
    menu_uninstall) en="Uninstall - remove containers and data"; ru="Удаление — контейнеры и данные" ;;
    menu_stop) en="Stop - shut down containers"; ru="Стоп — остановить контейнеры" ;;
    menu_restart) en="Restart - stop then start"; ru="Перезапуск — стоп, затем старт" ;;
    menu_update) en="Update - download latest and rebuild"; ru="Обновление — скачать и пересобрать" ;;
    menu_check_updates) en="Check for updates"; ru="Проверить обновления" ;;
    menu_help) en="Help - show commands"; ru="Справка — команды" ;;
    menu_quit) en="Quit"; ru="Выход" ;;
    prompt_missing) en="Not installed — what do you want to do?"; ru="Не установлено — что сделать?" ;;
    prompt_stopped) en="Stopped — what do you want to do?"; ru="Остановлено — что сделать?" ;;
    prompt_running) en="Running — what do you want to do?"; ru="Запущено — что сделать?" ;;
    prompt_default) en="What do you want to do?"; ru="Что сделать?" ;;
    prompt_update) en="Update available — what do you want to do?"; ru="Доступно обновление — что сделать?" ;;
    bye) en="Bye."; ru="Пока." ;;
    confirm_uninstall) en="Uninstall Task Studio? Containers and local data will be removed."; ru="Удалить Task Studio? Будут удалены контейнеры и локальные данные." ;;
    boot_downloading) en="Downloading Task Studio Launcher into %s …"; ru="Скачивание Task Studio Launcher в %s …" ;;
    boot_starting) en="Starting Task Studio Launcher…"; ru="Запуск Task Studio Launcher…" ;;
    boot_starting_new_window) en="Opening Task Studio Launcher in a new window…"; ru="Открытие Task Studio Launcher в новом окне…" ;;
    shortcut_main) en="Task Studio Launcher"; ru="Task Studio Launcher" ;;
    shortcut_uninstall) en="Task Studio Launcher — Uninstall"; ru="Task Studio Launcher — Удаление" ;;
    shortcut_comment) en="Task Studio Launcher"; ru="Task Studio Launcher" ;;
    status_starting_ts) en="Starting Task Studio"; ru="Запуск Task Studio" ;;
    usage_header) en="Task Studio Launcher"; ru="Task Studio Launcher" ;;
    confirm_purge) en="Also delete the install folder (launcher scripts included)?"; ru="Также удалить папку установки (включая лаунчер)?" ;;
    unknown_choice) en="Unknown choice: %s"; ru="Неизвестный выбор: %s" ;;
    unknown_command) en="Unknown command: %s"; ru="Неизвестная команда: %s" ;;

    help_title) en="Help"; ru="Справка" ;;
    help_line_menu) en="studio.sh              Interactive manager"; ru="studio.sh              Интерактивный менеджер" ;;
    help_line_install) en="studio.sh install      Build and configure"; ru="studio.sh install      Сборка и настройка" ;;
    help_line_start) en="studio.sh start        Run app + open browser"; ru="studio.sh start        Запуск + браузер" ;;
    help_line_open) en="studio.sh open         Open web UI in browser"; ru="studio.sh open         Открыть web UI в браузере" ;;
    help_line_stop) en="studio.sh stop         Shut down containers"; ru="studio.sh stop         Остановка контейнеров" ;;
    help_line_restart) en="studio.sh restart      Stop then start"; ru="studio.sh restart      Стоп, затем старт" ;;
    help_line_update) en="studio.sh update       Pull latest + rebuild"; ru="studio.sh update       Скачать обновление + пересборка" ;;
    help_line_uninstall) en="studio.sh uninstall    Remove stack (--purge)"; ru="studio.sh uninstall    Удалить стек (--purge)" ;;
    help_update_note1) en="On start, studio checks the remote version manifest (throttled)."; ru="При старте studio проверяет удалённый манифест версии (с ограничением частоты)." ;;
    help_update_note2) en="Update downloads an archive, compares checksums, replaces app files."; ru="Update скачивает архив, сверяет контрольные суммы, заменяет файлы приложения." ;;
    help_update_note3) en="User data is preserved: data/, .env, local compose overrides."; ru="Данные пользователя сохраняются: data/, .env, локальные compose-overrides." ;;

    # docker
    err_docker_missing) en="Docker not found. Install Docker Desktop (macOS/Windows) or Docker Engine + Compose v2 (Linux), then start it and retry."; ru="Docker не найден. Установите Docker Desktop (macOS/Windows) или Docker Engine + Compose v2 (Linux), запустите его и повторите." ;;
    err_docker_unusable) en="Docker is installed but not usable. Start Docker Desktop / the Docker daemon and wait until it is ready. Detail: %s"; ru="Docker установлен, но недоступен. Запустите Docker Desktop / демон Docker и дождитесь готовности. Подробности: %s" ;;
    err_docker_stopped) en="Docker is installed but not running. Start Docker Desktop / the Docker daemon and wait until it is ready."; ru="Docker установлен, но не запущен. Запустите Docker Desktop / демон Docker и дождитесь готовности." ;;
    err_docker_desktop_engine) en="Docker Desktop engine is not running (named pipe missing). Open Docker Desktop, wait until it says Running / Engine running, then retry. WSL 2 backend must be enabled."; ru="Движок Docker Desktop не запущен (нет named pipe). Откройте Docker Desktop, дождитесь статуса Running, затем повторите. Нужен backend WSL 2." ;;
    err_docker_start_failed) en="Could not start Docker automatically. Start Docker Desktop / enable the docker service, wait until it is ready, then retry."; ru="Не удалось запустить Docker автоматически. Запустите Docker Desktop / службу docker, дождитесь готовности и повторите." ;;
    err_compose_missing) en="Docker Compose v2 is required (command: docker compose). Update Docker Desktop or install the compose plugin."; ru="Нужен Docker Compose v2 (команда: docker compose). Обновите Docker Desktop или установите плагин compose." ;;
    err_buildkit) en="Docker Engine %s is too old. Task Studio needs Docker 20+ with BuildKit (cache mounts). Upgrade Docker Desktop / Engine."; ru="Docker Engine %s слишком старый. Нужен Docker 20+ с BuildKit (cache mounts). Обновите Docker Desktop / Engine." ;;

    # install bootstrap
    boot_git_missing) en="git not found."; ru="git не найден." ;;
    boot_updating) en="Updating existing install…"; ru="Обновление существующей установки…" ;;
    boot_studio_missing) en="studio.sh not found under %s/scripts"; ru="studio.sh не найден в %s/scripts" ;;
    boot_shortcuts) en="Installing console and desktop shortcut…"; ru="Установка консоли и ярлыка на рабочий стол…" ;;
    boot_shortcut_warn) en="Warning: could not create desktop shortcut (you can still run: bash %s/scripts/studio.sh)."; ru="Предупреждение: не удалось создать ярлык (можно запустить: bash %s/scripts/studio.sh)." ;;
    boot_ps_prepare) en="Preparing PowerShell execution and desktop shortcut…"; ru="Подготовка PowerShell и ярлыка на рабочий стол…" ;;
    boot_ps_shortcut_fail) en="Warning: desktop shortcut failed — %s"; ru="Предупреждение: ярлык не создан — %s" ;;
    boot_ps_fallback) en="  You can still start: %s"; ru="  Можно запустить вручную: %s" ;;
    boot_ps_studio_missing) en="studio.ps1 not found under %s\scripts"; ru="studio.ps1 не найден в %s\scripts" ;;
    boot_ps_git_missing) en="git not found. Install Git for Windows, then re-run: irm …/install.ps1 | iex"; ru="git не найден. Установите Git for Windows и снова выполните: irm …/install.ps1 | iex" ;;


    # ops titles / stages
    title_install) en="Install"; ru="Установка" ;;
    title_start) en="Start"; ru="Старт" ;;
    title_open) en="Open"; ru="Открыть" ;;
    title_stop) en="Stop"; ru="Стоп" ;;
    title_restart) en="Restart"; ru="Перезапуск" ;;
    title_uninstall) en="Uninstall"; ru="Удаление" ;;
    title_update) en="Update"; ru="Обновление" ;;
    stage_prepare) en="Prepare"; ru="Подготовка" ;;
    stage_build) en="Build images"; ru="Сборка образов" ;;
    stage_start) en="Start containers"; ru="Запуск контейнеров" ;;
    stage_health) en="Health check"; ru="Проверка готовности" ;;
    stage_model) en="AI model"; ru="Модель ИИ" ;;
    stage_finish) en="Finish"; ru="Завершение" ;;
    stage_stop) en="Stop containers"; ru="Остановка контейнеров" ;;
    stage_remove) en="Remove volumes and images"; ru="Удаление томов и образов" ;;
    stage_files) en="Remove local data"; ru="Удаление локальных данных" ;;
    stage_check) en="Check version"; ru="Проверка версии" ;;
    stage_download) en="Download package"; ru="Скачивание пакета" ;;
    stage_verify) en="Compare checksums"; ru="Сверка контрольных сумм" ;;
    stage_apply) en="Replace app files"; ru="Замена файлов приложения" ;;
    stage_rebuild) en="Rebuild stack"; ru="Пересборка стека" ;;

    status_check_docker) en="Checking Docker and environment"; ru="Проверка Docker и окружения" ;;
    status_docker_starting) en="Docker is not ready — starting it…"; ru="Docker не готов — запускаю…" ;;
    status_docker_waiting) en="Waiting for Docker… %ss / %ss"; ru="Ожидание Docker… %s с / %s с" ;;
    status_starting_infra) en="Starting databases and brokers…"; ru="Запуск баз и брокеров…" ;;
    status_starting_catalog) en="Starting catalog service…"; ru="Запуск сервиса catalog…" ;;
    status_waiting_catalog) en="Waiting for catalog… %ss left"; ru="Ожидание catalog… осталось %s с" ;;
    status_ensure_repo) en="Ensuring repository and .env"; ru="Проверка репозитория и .env" ;;
    status_build_slow) en="Building container images (first run is slow)"; ru="Сборка образов контейнеров (первый запуск долгий)" ;;
    status_starting_containers) en="Starting containers"; ru="Запуск контейнеров" ;;
    status_waiting_ui) en="Waiting for UI at %s"; ru="Ожидание UI: %s" ;;
    status_ui_ok) en="UI is responding"; ru="UI отвечает" ;;
    status_pull_model) en="Pulling Ollama model"; ru="Загрузка модели Ollama" ;;
    status_shortcuts) en="Shortcuts and permissions"; ru="Ярлыки и права" ;;
    status_shortcuts_skip) en="Shortcuts skipped (optional)"; ru="Ярлыки пропущены (необязательно)" ;;
    status_locate) en="Locating install and checking Docker"; ru="Поиск установки и проверка Docker" ;;
    status_check_ui) en="Checking UI (%s)"; ru="Проверка UI (%s)" ;;
    status_locate_short) en="Locating install"; ru="Поиск установки" ;;
    status_stopping) en="Stopping containers"; ru="Остановка контейнеров" ;;
    status_ensure_stopped) en="Ensuring all containers are stopped"; ru="Остановка всех контейнеров" ;;
    status_remove_vol) en="Removing volumes and local images"; ru="Удаление томов и локальных образов" ;;
    status_remove_files) en="Removing shortcuts, data/, .env"; ru="Удаление ярлыков, data/, .env" ;;
    status_cleanup) en="Cleanup"; ru="Очистка" ;;
    status_stop_before_update) en="Stopping containers before update"; ru="Остановка контейнеров перед обновлением" ;;
    status_already_stopped) en="Stack already stopped"; ru="Стек уже остановлен" ;;
    status_downloading_ver) en="Downloading %s"; ru="Скачивание %s" ;;
    status_compare_hash) en="Comparing content checksums (user data excluded)"; ru="Сравнение контрольных сумм (без данных пользователя)" ;;
    status_hash_same) en="Checksum unchanged — only version stamp"; ru="Контрольная сумма та же — только метка версии" ;;
    status_replace_files) en="Replacing app files (preserving data/ and .env)"; ru="Замена файлов приложения (data/ и .env сохраняются)" ;;
    status_rebuild) en="Rebuilding and starting stack"; ru="Пересборка и запуск стека" ;;
    status_no_env) en="No .env yet — use Install from the menu"; ru="Ещё нет .env — выберите Установку в меню" ;;
    status_up_to_date) en="Already up to date (%s)"; ru="Уже актуально (%s)" ;;
    status_read_remote) en="Reading remote version"; ru="Чтение удалённой версии" ;;
    status_ram_power) en="RAM ≈%s GB — power_saving mode"; ru="ОЗУ ≈%s ГБ — режим power_saving" ;;
    status_build_parallel) en="Compose parallel builds limited to %s (RAM-safe)"; ru="Параллельная сборка Compose ограничена до %s (бережём ОЗУ)" ;;
    status_skip_metrics) en="Skipping host-metrics (Docker Desktop / non-Linux)"; ru="Пропуск host-metrics (Docker Desktop / не Linux)" ;;
    status_skip_metrics_short) en="Skipping host-metrics profile"; ru="Пропуск профиля host-metrics" ;;
    status_removed_data) en="Removed data/"; ru="Удалён data/" ;;
    status_removed_env) en="Removed .env"; ru="Удалён .env" ;;
    status_deleting_root) en="Deleting %s"; ru="Удаление %s" ;;
    status_delete_scheduled) en="Folder delete scheduled (separate process): %s"; ru="Удаление папки запланировано (отдельный процесс): %s" ;;
    status_purge_skip) en="--purge skipped — path is not %s"; ru="--purge пропущен — путь не %s" ;;
    status_repo_kept) en="Install folder kept (launcher scripts remain)."; ru="Папка установки сохранена (лаунчер остаётся)." ;;

    info_clone) en="Repository not found — cloning into %s …"; ru="Репозиторий не найден — клонирование в %s …" ;;
    info_env_created) en="Created .env from .env.example"; ru="Создан .env из .env.example" ;;
    info_secrets_key) en="Generated SECRETS_MASTER_KEY"; ru="Сгенерирован SECRETS_MASTER_KEY" ;;
    info_jwt) en="Generated JWT_SECRET"; ru="Сгенерирован JWT_SECRET" ;;
    info_pull_model) en="Pulling Ollama model: %s (may take a while)…"; ru="Загрузка модели Ollama: %s (может занять время)…" ;;
    info_cancelled) en="Cancelled."; ru="Отменено." ;;
    info_dir) en="Directory: %s"; ru="Каталог: %s" ;;
    info_ui) en="UI: %s"; ru="UI: %s" ;;
    info_opened_ui) en="Opened %s"; ru="Открыто: %s" ;;
    warn_catalog_continue) en="catalog is not healthy — continuing with UI and the rest of the stack"; ru="catalog не healthy — продолжаем запуск UI и остальных сервисов" ;;
    warn_ui_unreachable) en="UI is not responding at %s. Use Heal, Restart, or Install/repair."; ru="UI не отвечает: %s. Используйте Починить, Перезапуск или Установка/ремонт." ;;
    info_open_manual) en="Open in browser: %s"; ru="Откройте в браузере: %s" ;;
    info_console) en="Console: bash ./scripts/studio.sh"; ru="Консоль: bash ./scripts/studio.sh" ;;
    info_console_ps) en="Console: .\scripts\studio.cmd"; ru="Консоль: .\scripts\studio.cmd" ;;

    warn_model_pull) en="Could not pull the model now. Later: docker compose -f %s --env-file .env --profile full exec ollama ollama pull %s"; ru="Не удалось скачать модель сейчас. Позже: docker compose -f %s --env-file .env --profile full exec ollama ollama pull %s" ;;
    warn_model_pull_short) en="Could not pull the model now."; ru="Не удалось скачать модель сейчас." ;;
    warn_path_wsl_mnt) en="Install path is on /mnt/... (%s). Prefer a Linux filesystem home (e.g. ~/task-studio) — NTFS mounts often break Postgres/ClickHouse permissions."; ru="Путь установки на /mnt/... (%s). Лучше домашний каталог Linux (например ~/task-studio) — монтирование NTFS часто ломает права Postgres/ClickHouse." ;;
    warn_path_windows) en="Install is on a Windows drive (%s). Prefer WSL home (~/task-studio) for Docker data dirs — NTFS bind mounts often break Postgres/ClickHouse."; ru="Установка на диске Windows (%s). Для каталогов data/ лучше WSL (~/task-studio) — bind-mount NTFS часто ломает Postgres/ClickHouse." ;;
    warn_shortcuts) en="Could not create shortcuts — %s"; ru="Не удалось создать ярлыки — %s" ;;
    warn_uninstall) en="This removes containers, volumes, local images, data/, shortcuts, and .env."; ru="Будут удалены контейнеры, тома, локальные образы, data/, ярлыки и .env." ;;
    warn_purge) en="The install folder will also be deleted (including the launcher): %s"; ru="Также будет удалена папка установки (включая лаунчер): %s" ;;
    warn_purge_ps) en="The install folder will also be deleted (including the launcher): %s"; ru="Также будет удалена папка установки (включая лаунчер): %s" ;;
    warn_purge_launcher) en="Consumer install: the whole folder will be removed after this process exits: %s"; ru="Пользовательская установка: после выхода будет удалена вся папка: %s" ;;
    warn_ui_after_update) en="Updated, but UI is not responding yet at %s"; ru="Обновлено, но UI пока не отвечает: %s" ;;
    warn_compose_down) en="compose down reported an error — %s"; ru="compose down сообщил об ошибке — %s" ;;

    err_ram) en="Detected ≈%s GB RAM; minimum to start is %s GB (16 GB recommended)."; ru="Обнаружено ≈%s ГБ ОЗУ; минимум для старта %s ГБ (рекомендуется 16 ГБ)." ;;
    err_build) en="Docker build failed. Check Docker is running and disk space is available."; ru="Сборка Docker не удалась. Проверьте, что Docker запущен и есть место на диске." ;;
    err_up) en="Failed to start containers (docker compose up)."; ru="Не удалось запустить контейнеры (docker compose up)." ;;
    err_ui) en="Containers started, but UI is not responding at %s"; ru="Контейнеры запущены, но UI не отвечает: %s" ;;
    err_openssl) en="openssl or python3 required to generate secrets"; ru="Для генерации секретов нужны openssl или python3" ;;
    err_git) en="git not found."; ru="git не найден." ;;
    err_not_installed) en="Installed Task Studio Launcher not found. Run: bash scripts/studio.sh install"; ru="Установка Task Studio Launcher не найдена. Выполните: bash scripts/studio.sh install" ;;
    err_not_installed_ps) en="Installed Task Studio Launcher not found. Run: .\scripts\studio.cmd install"; ru="Установка Task Studio Launcher не найдена. Выполните: .\scripts\studio.cmd install" ;;
    err_up_short) en="Failed to start containers."; ru="Не удалось запустить контейнеры." ;;
    err_compose_missing_file) en="Not found: %s. Run from the repository root."; ru="Не найдено: %s. Запустите из корня репозитория." ;;
    err_no_env_stop) en="No .env file — nothing to stop."; ru="Нет файла .env — останавливать нечего." ;;
    err_still_running) en="Some containers are still running. Try again or check: docker compose ps"; ru="Часть контейнеров ещё работает. Повторите или проверьте: docker compose ps" ;;
    err_no_env_install) en="No .env file — run install first."; ru="Нет файла .env — сначала выполните установку." ;;
    err_stop_before_restart) en="Could not stop all containers before restart."; ru="Не удалось остановить все контейнеры перед перезапуском." ;;
    err_up_after_restart) en="Failed to start containers after restart."; ru="Не удалось запустить контейнеры после перезапуска." ;;
    err_ui_after_restart) en="Restarted, but the UI is not responding at %s."; ru="Перезапущено, но UI не отвечает: %s." ;;
    err_unknown_opt) en="Unknown option: %s"; ru="Неизвестный параметр: %s" ;;
    err_install_not_found) en="Task Studio Launcher install not found."; ru="Установка Task Studio Launcher не найдена." ;;
    err_uninstall_running) en="Cannot uninstall while containers are still running."; ru="Нельзя удалять, пока контейнеры ещё работают." ;;
    err_robocopy) en="robocopy not found (required for safe update on Windows)."; ru="robocopy не найден (нужен для безопасного обновления в Windows)." ;;
    err_update_dev) en="Self-update is only for the consumer install (%s). Developer trees are left untouched."; ru="Самообновление только для пользовательской установки (%s). Дерево разработчика не трогаем." ;;
    err_update_check) en="Update check failed: %s"; ru="Проверка обновлений не удалась: %s" ;;
    err_stop_before_update) en="Stop containers before updating."; ru="Остановите контейнеры перед обновлением." ;;
    err_curl) en="curl not found."; ru="curl не найден." ;;
    err_tar) en="tar not found."; ru="tar не найден." ;;
    err_download) en="Failed to download update archive."; ru="Не удалось скачать архив обновления." ;;
    err_unpack) en="Failed to unpack update archive."; ru="Не удалось распаковать архив обновления." ;;
    err_layout) en="Update archive has unexpected layout."; ru="Неожиданная структура архива обновления." ;;
    err_fingerprint) en="Could not fingerprint downloaded package."; ru="Не удалось посчитать отпечаток скачанного пакета." ;;
    err_sync) en="Failed to sync application files."; ru="Не удалось синхронизировать файлы приложения." ;;
    err_env_gone) en="Safety abort: .env disappeared during update."; ru="Аварийный стоп: .env пропал во время обновления." ;;
    err_build_update) en="Docker build failed after update."; ru="Сборка Docker не удалась после обновления." ;;
    err_up_update) en="Failed to start containers after update."; ru="Не удалось запустить контейнеры после обновления." ;;
    err_leave_root) en="Cannot leave %s to delete it."; ru="Нельзя выйти из %s, чтобы удалить папку." ;;

    upd_unknown) en="unknown error"; ru="неизвестная ошибка" ;;
    upd_summary) en="Update %s → %s"; ru="Обновление %s → %s" ;;
    upd_up_to_date) en="Up to date (%s)"; ru="Актуально (%s)" ;;
    upd_offline) en="Could not reach version manifest (offline?)"; ru="Не удалось получить манифест версии (нет сети?)" ;;
    upd_invalid) en="Invalid version manifest"; ru="Некорректный манифест версии" ;;
    upd_unsupported) en="Developer tree — self-update disabled (consumer install only)"; ru="Дерево разработчика — самообновление отключено (только пользовательская установка)" ;;
    upd_curl_missing) en="curl not found"; ru="curl не найден" ;;

    usage_body) en="Usage:
  bash scripts/studio.sh              Interactive dialog manager
  bash scripts/studio.sh install      First-time setup / rebuild
  bash scripts/studio.sh start        Start stack + open UI
  bash scripts/studio.sh open         Open web UI in browser
  bash scripts/studio.sh stop         Stop stack
  bash scripts/studio.sh restart      Stop then start
  bash scripts/studio.sh uninstall    Remove stack (add --purge to delete folder)
  bash scripts/studio.sh update       Pull latest code and rebuild
  bash scripts/studio.sh help         This help

Menu actions depend on stack state (not installed / stopped / running).
On open, studio checks a remote version file (about once per hour).
Update downloads a package, compares checksums, and replaces app files.
User data (data/, .env) is never overwritten. Update is never silent."; ru="Использование:
  bash scripts/studio.sh              Интерактивный менеджер
  bash scripts/studio.sh install      Первая установка / пересборка
  bash scripts/studio.sh start        Запуск стека + UI
  bash scripts/studio.sh open         Открыть web UI в браузере
  bash scripts/studio.sh stop         Остановка
  bash scripts/studio.sh restart      Стоп, затем старт
  bash scripts/studio.sh uninstall    Удаление стека (добавьте --purge, чтобы стереть папку)
  bash scripts/studio.sh update       Скачать обновление и пересобрать
  bash scripts/studio.sh help         Эта справка

Пункты меню зависят от состояния стека (не установлено / остановлено / запущено).
При открытии studio проверяет удалённый файл версии (примерно раз в час).
Update скачивает пакет, сверяет контрольные суммы и заменяет файлы приложения.
Данные пользователя (data/, .env) не затираются. Обновление никогда не тихое." ;;

    *)
      en="$key"
      ru="$key"
      ;;
  esac
  if [[ "${TS_UI_LANG:-en}" == "ru" ]]; then
    text="$ru"
  else
    text="$en"
  fi
  if [[ "$#" -gt 0 ]]; then
    # shellcheck disable=SC2059
    printf "$text\n" "$@"
  else
    printf '%s\n' "$text"
  fi
}

# Auto-detect once on source (can be re-run).
if [[ -z "${TS_UI_LANG}" ]]; then
  ts_detect_lang
fi
