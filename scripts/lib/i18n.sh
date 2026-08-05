
TS_UI_LANG="${TS_UI_LANG:-}"

ts_detect_lang() {
  local loc=""
  loc="${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}"
  if [[ -z "$loc" || "$loc" == "C" || "$loc" == "POSIX" ]]; then
    if [[ "$(uname -s 2>/dev/null || true)" == "Darwin" ]] && command -v defaults >/dev/null 2>&1; then
      loc="$(defaults read -g AppleLocale 2>/dev/null || true)"
    fi
  fi
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
    enter_back) en="Enter — return"; ru="Enter — назад" ;;
    press_enter_close) en="Press Enter to close…"; ru="Нажмите Enter, чтобы закрыть…" ;;
    shortcut_fail_exit) en="Task Studio Launcher stopped with exit code %s."; ru="Task Studio Launcher завершился с кодом %s." ;;
    shortcut_blocked_hint) en="If the script is blocked, run it from Terminal:"; ru="Если скрипт заблокирован, запустите его из Terminal:" ;;
    warn_desktop_unwritable) en="Cannot write to the desktop folder: %s"; ru="Нет доступа на запись в папку рабочего стола: %s" ;;
    shortcuts_created) en="Desktop shortcuts: %s"; ru="Ярлыки на рабочем столе: %s" ;;
    cmd_failed_short) en="The command failed."; ru="Команда завершилась с ошибкой." ;;
    status_creating_shortcuts) en="Creating desktop shortcuts…"; ru="Создание ярлыков на рабочем столе…" ;;
    status_checking_ui_plain) en="Checking the web interface…"; ru="Проверка веб-интерфейса…" ;;
    warn_purge_skip_got) en="-Purge skipped: path is not %s (current: %s)."; ru="-Purge пропущен: путь не %s (сейчас: %s)." ;;
    warn_refresh_shortcuts) en="Could not refresh desktop shortcuts: %s"; ru="Не удалось обновить ярлыки на рабочем столе: %s" ;;
    err_build_short) en="Docker image build failed."; ru="Сборка образов Docker не удалась." ;;
    err_robocopy_code) en="robocopy failed with code %s."; ru="robocopy завершился с кодом %s." ;;
    type_yes_continue) en="Type YES to continue:"; ru="Введите YES, чтобы продолжить:" ;;
    type_yes_hint) en="Type YES in uppercase to confirm. Any other input cancels."; ru="Введите YES заглавными буквами, чтобы подтвердить. Любой другой ввод отменяет действие." ;;
    confirm_continue) en="Continue?"; ru="Продолжить?" ;;
    press_enter_menu) en="Press Enter to return to the menu…"; ru="Нажмите Enter, чтобы вернуться в меню…" ;;
    enter_continue) en="Enter — continue"; ru="Enter — дальше" ;;
    returning_footer) en="Returning in %s s · Enter — now"; ru="Возврат через %s с · Enter — сразу" ;;
    menu_footer) en="↑↓ move · Enter select · q quit"; ru="↑↓ перемещение · Enter выбрать · q выход" ;;
    menu_footer_ps) en="↑↓ move · Enter select · Esc quit"; ru="↑↓ перемещение · Enter выбрать · Esc выход" ;;
    prog_footer_idle) en="Progress view · Enter when finished"; ru="Экран прогресса · Enter, когда готово" ;;
    prog_footer_run) en="Working… please wait"; ru="Идёт работа… подождите" ;;
    prog_footer_return) en="Enter — back · auto-return in 5 s"; ru="Enter — назад · автовозврат через 5 с" ;;
    prog_details) en="Log file: %s"; ru="Файл журнала: %s" ;;
    prog_details_ps) en="Log file: %s"; ru="Файл журнала: %s" ;;
    prog_log_hint) en="Full log: %s"; ru="Полный журнал: %s" ;;
    prog_eta_sec) en="About %s s remaining"; ru="Осталось около %s с" ;;
    prog_eta_min) en="About %s min remaining"; ru="Осталось около %s мин" ;;
    prog_eta_hm) en="About %s h %s min remaining"; ru="Осталось около %s ч %s мин" ;;
    prog_eta_failed) en="failed"; ru="ошибка" ;;
    prog_eta_finishing) en="Finishing…"; ru="Завершение…" ;;
    prog_eta_done) en="done"; ru="готово" ;;
    prog_spinner_frames) en="|/-\\"; ru="|/-\\" ;;
    prog_error_label) en="Error"; ru="Ошибка" ;;
    prog_unknown_error) en="Unknown error"; ru="Неизвестная ошибка" ;;
    prog_completed) en="Completed successfully"; ru="Успешно завершено" ;;
    done_returning) en="Done. Returning to the menu in 5 s…"; ru="Готово. Возврат в меню через 5 с…" ;;
    prog_starting) en="Starting…"; ru="Запуск…" ;;
    prog_done) en="Done"; ru="Готово" ;;
    prog_failed) en="Failed"; ru="Ошибка" ;;
    prog_finished_ok) en="Finished successfully"; ru="Успешно завершено" ;;
    cmd_failed) en="The command failed (exit code %s)."; ru="Команда завершилась с ошибкой (код %s)." ;;
    err_progress_empty_log) en="The command failed before writing a log. Often data/logs is not writable because Docker owns data/. Log path: %s"; ru="Команда завершилась до записи журнала. Часто каталог data/logs недоступен для записи (data/ создал Docker). Путь к журналу: %s" ;;
    menu_install) en="First install"; ru="Первичная установка" ;;
    menu_start) en="Start stack"; ru="Запустить стек" ;;
    menu_heal) en="Repair stack"; ru="Починить стек" ;;
    menu_open) en="Open app"; ru="Открыть приложение" ;;
    menu_install_repair) en="Rebuild packages"; ru="Пересборка пакетов" ;;
    menu_uninstall) en="Remove app"; ru="Удалить приложение" ;;
    menu_stop) en="Stop work"; ru="Остановить работу" ;;
    menu_restart) en="Restart app"; ru="Перезапуск приложения" ;;
    menu_update) en="Update app"; ru="Обновить приложение" ;;
    menu_check_updates) en="Check updates"; ru="Проверить обновления" ;;
    menu_help) en="Help (CLI)"; ru="Справка (CLI)" ;;
    menu_quit) en="Quit"; ru="Выход" ;;
    prompt_missing) en="Task Studio is not installed yet. Choose an action:"; ru="Task Studio ещё не установлен. Выберите действие:" ;;
    prompt_stopped) en="The stack is stopped. Choose an action:"; ru="Стек остановлен. Выберите действие:" ;;
    prompt_running) en="The stack is running. Choose an action:"; ru="Стек запущен. Выберите действие:" ;;
    prompt_default) en="Choose an action:"; ru="Выберите действие:" ;;
    prompt_update) en="An update is available. Choose an action:"; ru="Доступно обновление. Выберите действие:" ;;
    bye) en="Goodbye."; ru="До свидания." ;;
    confirm_uninstall) en="Uninstall Task Studio? Containers and local data will be removed."; ru="Удалить Task Studio? Будут удалены контейнеры и локальные данные." ;;
    boot_downloading) en="Downloading Task Studio Launcher into %s…"; ru="Скачивание Task Studio Launcher в %s…" ;;
    boot_starting) en="Starting Task Studio Launcher…"; ru="Запуск Task Studio Launcher…" ;;
    boot_starting_new_window) en="Opening Task Studio Launcher in a new window…"; ru="Открытие Task Studio Launcher в новом окне…" ;;
    shortcut_main) en="Task Studio Launcher"; ru="Task Studio Launcher" ;;
    shortcut_uninstall) en="Task Studio Launcher — Uninstall"; ru="Task Studio Launcher — Удаление" ;;
    shortcut_comment) en="Task Studio Launcher"; ru="Task Studio Launcher" ;;
    status_starting_ts) en="Starting Task Studio…"; ru="Запуск Task Studio…" ;;
    usage_header) en="Task Studio Launcher"; ru="Task Studio Launcher" ;;
    confirm_purge) en="Also delete the install folder (including the launcher)?"; ru="Также удалить папку установки (включая лаунчер)?" ;;
    unknown_choice) en="Unknown choice: %s"; ru="Неизвестный выбор: %s" ;;
    unknown_command) en="Unknown command: %s"; ru="Неизвестная команда: %s" ;;
    help_title) en="Help"; ru="Справка" ;;
    help_line_menu) en="studio.sh              Interactive manager"; ru="studio.sh              Интерактивный менеджер" ;;
    help_line_install) en="studio.sh install      First setup and configuration"; ru="studio.sh install      Первая настройка и конфигурация" ;;
    help_line_start) en="studio.sh start        Start all containers"; ru="studio.sh start        Запуск всех контейнеров" ;;
    help_line_open) en="studio.sh open         Open the web interface"; ru="studio.sh open         Открыть веб-интерфейс" ;;
    help_line_stop) en="studio.sh stop         Stop all containers"; ru="studio.sh stop         Остановка всех контейнеров" ;;
    help_line_restart) en="studio.sh restart      Stop, then start again"; ru="studio.sh restart      Остановить и запустить снова" ;;
    help_line_update) en="studio.sh update       Download update and rebuild"; ru="studio.sh update       Скачать обновление и пересобрать" ;;
    help_line_uninstall) en="studio.sh uninstall    Remove the stack (--purge)"; ru="studio.sh uninstall    Удалить стек (--purge)" ;;
    help_update_note1) en="On open, the launcher checks the remote version manifest (about once per hour)."; ru="При открытии лаунчер проверяет удалённый манифест версии (примерно раз в час)." ;;
    help_update_note2) en="Update downloads an archive, verifies checksums, and replaces application files."; ru="Обновление скачивает архив, сверяет контрольные суммы и заменяет файлы приложения." ;;
    help_update_note3) en="Your data is kept: data/, .env, and local Compose overrides."; ru="Ваши данные сохраняются: data/, .env и локальные переопределения Compose." ;;
    err_docker_missing) en="Docker was not found. Install Docker Desktop (macOS/Windows) or Docker Engine with Compose v2 (Linux), start it, then try again."; ru="Docker не найден. Установите Docker Desktop (macOS/Windows) или Docker Engine с Compose v2 (Linux), запустите его и повторите попытку." ;;
    err_docker_unusable) en="Docker is installed but not usable. Start Docker Desktop or the Docker daemon and wait until it is ready. Details: %s"; ru="Docker установлен, но недоступен. Запустите Docker Desktop или демон Docker и дождитесь готовности. Подробности: %s" ;;
    err_docker_stopped) en="Docker is installed but not running. Start Docker Desktop or the Docker daemon and wait until it is ready."; ru="Docker установлен, но не запущен. Запустите Docker Desktop или демон Docker и дождитесь готовности." ;;
    err_docker_desktop_engine) en="The Docker Desktop engine is not running (named pipe missing). Open Docker Desktop, wait until it shows Running, then try again. The WSL 2 backend must be enabled."; ru="Движок Docker Desktop не запущен (нет named pipe). Откройте Docker Desktop, дождитесь статуса Running и повторите попытку. Нужен backend WSL 2." ;;
    err_docker_start_failed) en="Could not start Docker automatically. Start Docker Desktop or enable the docker service, wait until it is ready, then try again."; ru="Не удалось запустить Docker автоматически. Запустите Docker Desktop или службу docker, дождитесь готовности и повторите попытку." ;;
    err_compose_missing) en="Docker Compose v2 is required (command: docker compose). Update Docker Desktop or install the Compose plugin."; ru="Нужен Docker Compose v2 (команда: docker compose). Обновите Docker Desktop или установите плагин Compose." ;;
    err_buildkit) en="Docker Engine %s is too old. Task Studio needs Docker 20+ with BuildKit (cache mounts). Please upgrade Docker Desktop or Engine."; ru="Docker Engine %s слишком старый. Task Studio нужен Docker 20+ с BuildKit (cache mounts). Обновите Docker Desktop или Engine." ;;
    boot_git_missing) en="git was not found."; ru="git не найден." ;;
    boot_updating) en="Updating the existing installation…"; ru="Обновление существующей установки…" ;;
    boot_studio_missing) en="studio.sh was not found under %s/scripts."; ru="studio.sh не найден в %s/scripts." ;;
    boot_shortcuts) en="Installing the console entry and desktop shortcut…"; ru="Установка пункта консоли и ярлыка на рабочем столе…" ;;
    boot_shortcut_warn) en="Warning: could not create a desktop shortcut. You can still run: bash %s/scripts/studio.sh"; ru="Предупреждение: не удалось создать ярлык. Можно запустить вручную: bash %s/scripts/studio.sh" ;;
    boot_ps_prepare) en="Preparing PowerShell and the desktop shortcut…"; ru="Подготовка PowerShell и ярлыка на рабочем столе…" ;;
    boot_ps_shortcut_fail) en="Warning: desktop shortcut was not created — %s"; ru="Предупреждение: ярлык на рабочем столе не создан — %s" ;;
    boot_ps_fallback) en="  You can still start with: %s"; ru="  Можно запустить вручную: %s" ;;
    boot_ps_studio_missing) en="studio.ps1 was not found under %s\\scripts."; ru="studio.ps1 не найден в %s\\scripts." ;;
    boot_ps_git_missing) en="git was not found. Install Git for Windows, then run again: irm …/install.ps1 | iex"; ru="git не найден. Установите Git for Windows и снова выполните: irm …/install.ps1 | iex" ;;
    title_install) en="Install"; ru="Установка" ;;
    title_rebuild_packages) en="Rebuild packages"; ru="Пересборка пакетов" ;;
    title_start) en="Start"; ru="Запуск" ;;
    title_open) en="Open"; ru="Открыть" ;;
    title_stop) en="Stop"; ru="Остановка" ;;
    title_restart) en="Restart"; ru="Перезапуск" ;;
    title_uninstall) en="Uninstall"; ru="Удаление" ;;
    title_update) en="Update"; ru="Обновление" ;;
    stage_prepare) en="Prepare"; ru="Подготовка" ;;
    stage_build) en="Build images"; ru="Сборка образов" ;;
    stage_start) en="Start containers"; ru="Запуск контейнеров" ;;
    stage_health) en="Readiness check"; ru="Проверка готовности" ;;
    stage_model) en="AI model"; ru="Модель ИИ" ;;
    stage_finish) en="Finish"; ru="Завершение" ;;
    stage_stop) en="Stop containers"; ru="Остановка контейнеров" ;;
    stage_remove) en="Remove volumes and images"; ru="Удаление томов и образов" ;;
    stage_files) en="Remove local data"; ru="Удаление локальных данных" ;;
    stage_check) en="Check version"; ru="Проверка версии" ;;
    stage_download) en="Download package"; ru="Скачивание пакета" ;;
    stage_verify) en="Verify checksums"; ru="Сверка контрольных сумм" ;;
    stage_apply) en="Replace application files"; ru="Замена файлов приложения" ;;
    stage_rebuild) en="Rebuild the stack"; ru="Пересборка стека" ;;
    status_check_docker) en="Checking Docker and the environment…"; ru="Проверка Docker и окружения…" ;;
    status_docker_starting) en="Docker is not ready — starting it…"; ru="Docker ещё не готов — запускаю…" ;;
    status_docker_waiting) en="Waiting for Docker… %s s / %s s"; ru="Ожидание Docker… %s с / %s с" ;;
    status_starting_infra) en="Starting databases and message brokers…"; ru="Запуск баз данных и брокеров сообщений…" ;;
    status_starting_catalog) en="Starting the catalog service…"; ru="Запуск сервиса catalog…" ;;
    status_waiting_catalog) en="Waiting for catalog… %s s left"; ru="Ожидание catalog… осталось %s с" ;;
    status_ensure_repo) en="Checking the repository and .env…"; ru="Проверка репозитория и файла .env…" ;;
    status_build) en="Building container images…"; ru="Сборка образов контейнеров…" ;;
    status_build_slow) en="Building container images (the first run takes longer)…"; ru="Сборка образов контейнеров (первый запуск занимает больше времени)…" ;;
    status_starting_containers) en="Starting containers…"; ru="Запуск контейнеров…" ;;
    status_waiting_ui) en="Waiting for the web interface at %s…"; ru="Ожидание веб-интерфейса: %s…" ;;
    status_ui_ok) en="The web interface is responding."; ru="Веб-интерфейс отвечает." ;;
    status_pull_model) en="Downloading the Ollama model…"; ru="Загрузка модели Ollama…" ;;
    status_shortcuts) en="Creating shortcuts and setting permissions…"; ru="Создание ярлыков и настройка прав…" ;;
    status_shortcuts_skip) en="Desktop shortcuts were skipped (optional step)."; ru="Ярлыки на рабочем столе пропущены (необязательный шаг)." ;;
    status_locate) en="Locating the installation and checking Docker…"; ru="Поиск установки и проверка Docker…" ;;
    status_check_ui) en="Checking the web interface (%s)…"; ru="Проверка веб-интерфейса (%s)…" ;;
    status_locate_short) en="Locating the installation…"; ru="Поиск установки…" ;;
    status_stopping) en="Stopping containers…"; ru="Остановка контейнеров…" ;;
    status_ensure_stopped) en="Making sure all containers are stopped…"; ru="Проверка, что все контейнеры остановлены…" ;;
    status_remove_vol) en="Removing volumes and local images…"; ru="Удаление томов и локальных образов…" ;;
    status_remove_files) en="Removing shortcuts, data/, and .env…"; ru="Удаление ярлыков, data/ и .env…" ;;
    status_cleanup) en="Cleaning up…"; ru="Очистка…" ;;
    status_stop_before_update) en="Stopping containers before the update…"; ru="Остановка контейнеров перед обновлением…" ;;
    status_already_stopped) en="The stack is already stopped."; ru="Стек уже остановлен." ;;
    status_downloading_ver) en="Downloading %s…"; ru="Скачивание %s…" ;;
    status_compare_hash) en="Comparing content checksums (user data excluded)…"; ru="Сравнение контрольных сумм содержимого (без данных пользователя)…" ;;
    status_hash_same) en="Checksum unchanged — only the version stamp will be updated."; ru="Контрольная сумма не изменилась — будет обновлена только метка версии." ;;
    status_replace_files) en="Replacing application files (data/ and .env are kept)…"; ru="Замена файлов приложения (data/ и .env сохраняются)…" ;;
    status_rebuild) en="Rebuilding and starting the stack…"; ru="Пересборка и запуск стека…" ;;
    status_no_env) en="No .env file yet — choose Install in the menu."; ru="Файла .env ещё нет — выберите «Установка» в меню." ;;
    status_up_to_date) en="Already up to date (%s)."; ru="Уже установлена актуальная версия (%s)." ;;
    status_read_remote) en="Reading the remote version…"; ru="Чтение удалённой версии…" ;;
    status_ram_power) en="About %s GB RAM detected — using power_saving mode."; ru="Обнаружено около %s ГБ ОЗУ — включён режим power_saving." ;;
    status_build_parallel) en="Compose parallel builds limited to %s to save RAM."; ru="Параллельная сборка Compose ограничена до %s, чтобы беречь ОЗУ." ;;
    status_skip_metrics) en="Skipping the host-metrics profile (Docker Desktop / non-Linux)."; ru="Пропуск профиля host-metrics (Docker Desktop / не Linux)." ;;
    status_skip_metrics_short) en="Skipping the host-metrics profile."; ru="Пропуск профиля host-metrics." ;;
    status_removed_data) en="Removed data/."; ru="Каталог data/ удалён." ;;
    status_removed_env) en="Removed .env."; ru="Файл .env удалён." ;;
    status_deleting_root) en="Deleting %s…"; ru="Удаление %s…" ;;
    status_delete_scheduled) en="Folder deletion scheduled in a separate process: %s"; ru="Удаление папки запланировано в отдельном процессе: %s" ;;
    status_purge_skip) en="--purge skipped: path is not %s."; ru="--purge пропущен: путь не %s." ;;
    status_repo_kept) en="The install folder was kept (launcher scripts remain)."; ru="Папка установки сохранена (скрипты лаунчера остаются)." ;;
    info_clone) en="Repository not found — cloning into %s…"; ru="Репозиторий не найден — клонирование в %s…" ;;
    info_env_created) en="Created .env from .env.example."; ru="Создан файл .env из .env.example." ;;
    info_secrets_key) en="Generated SECRETS_MASTER_KEY."; ru="Сгенерирован SECRETS_MASTER_KEY." ;;
    info_jwt) en="Generated JWT_SECRET."; ru="Сгенерирован JWT_SECRET." ;;
    info_pull_model) en="Downloading Ollama model %s (this may take a while)…"; ru="Загрузка модели Ollama %s (это может занять время)…" ;;
    info_cancelled) en="Cancelled."; ru="Отменено." ;;
    info_dir) en="Install directory: %s"; ru="Каталог установки: %s" ;;
    info_ui) en="Web interface: %s"; ru="Веб-интерфейс: %s" ;;
    info_opened_ui) en="Opened %s"; ru="Открыто: %s" ;;
    warn_catalog_continue) en="The catalog service is not ready yet — continuing with the web interface and the rest of the stack."; ru="Сервис catalog ещё не готов — продолжаем запуск веб-интерфейса и остальных сервисов." ;;
    warn_ui_unreachable) en="The web interface is not responding at %s. Try Repair stack, Restart app, or Rebuild packages."; ru="Веб-интерфейс не отвечает: %s. Попробуйте «Починить стек», «Перезапуск приложения» или «Пересборка пакетов»." ;;
    info_open_manual) en="Open in the browser: %s"; ru="Откройте в браузере: %s" ;;
    info_console) en="Console: bash ./scripts/studio.sh"; ru="Консоль: bash ./scripts/studio.sh" ;;
    info_console_ps) en="Console: .\\scripts\\studio.cmd"; ru="Консоль: .\\scripts\\studio.cmd" ;;
    warn_model_pull) en="Could not download the model now. Later run: docker compose -f %s --env-file .env --profile full exec ollama ollama pull %s"; ru="Не удалось скачать модель сейчас. Позже выполните: docker compose -f %s --env-file .env --profile full exec ollama ollama pull %s" ;;
    warn_model_pull_short) en="Could not download the model now."; ru="Не удалось скачать модель сейчас." ;;
    warn_path_wsl_mnt) en="Install path is under /mnt/... (%s). Prefer a Linux home path (for example ~/task-studio) — NTFS mounts often break Postgres and ClickHouse permissions."; ru="Путь установки на /mnt/... (%s). Лучше домашний каталог Linux (например ~/task-studio): монтирование NTFS часто ломает права Postgres и ClickHouse." ;;
    warn_path_windows) en="Install is on a Windows drive (%s). Prefer a WSL home path (~/task-studio) for data/ — NTFS bind mounts often break Postgres and ClickHouse."; ru="Установка на диске Windows (%s). Для каталогов data/ лучше путь в WSL (~/task-studio): bind-mount NTFS часто ломает Postgres и ClickHouse." ;;
    warn_shortcuts) en="Could not create desktop shortcuts: %s"; ru="Не удалось создать ярлыки на рабочем столе: %s" ;;
    warn_uninstall) en="This removes containers, volumes, local images, data/, shortcuts, and .env."; ru="Будут удалены контейнеры, тома, локальные образы, data/, ярлыки и .env." ;;
    warn_purge) en="The install folder will also be deleted (including the launcher): %s"; ru="Также будет удалена папка установки (включая лаунчер): %s" ;;
    warn_purge_ps) en="The install folder will also be deleted (including the launcher): %s"; ru="Также будет удалена папка установки (включая лаунчер): %s" ;;
    warn_purge_launcher) en="Consumer install: the whole folder will be removed after this process exits: %s"; ru="Пользовательская установка: после выхода процесса будет удалена вся папка: %s" ;;
    warn_ui_after_update) en="Update finished, but the web interface is not responding yet at %s."; ru="Обновление завершено, но веб-интерфейс пока не отвечает: %s." ;;
    warn_compose_down) en="docker compose down reported an error: %s"; ru="docker compose down сообщил об ошибке: %s" ;;
    err_ram) en="Detected about %s GB RAM; the minimum to start is %s GB (16 GB recommended)."; ru="Обнаружено около %s ГБ ОЗУ; минимум для запуска — %s ГБ (рекомендуется 16 ГБ)." ;;
    err_build) en="Docker image build failed. Check that Docker is running and that disk space is available."; ru="Сборка образов Docker не удалась. Проверьте, что Docker запущен и на диске достаточно места." ;;
    err_up) en="Failed to start containers (docker compose up)."; ru="Не удалось запустить контейнеры (docker compose up)." ;;
    err_ui) en="Containers started, but the web interface is not responding at %s."; ru="Контейнеры запущены, но веб-интерфейс не отвечает: %s." ;;
    err_ui_port_conflict) en="Containers started, but http://127.0.0.1:%s is used by another program (not Task Studio). Open %s, or set TASK_STUDIO_HTTP_PORT to a free port and restart."; ru="Контейнеры запущены, но http://127.0.0.1:%s занят другой программой (не Task Studio). Откройте %s или задайте свободный TASK_STUDIO_HTTP_PORT и перезапустите." ;;
    err_openssl) en="openssl or python3 is required to generate secrets."; ru="Для генерации секретов нужны openssl или python3." ;;
    err_git) en="git was not found."; ru="git не найден." ;;
    err_not_installed) en="Task Studio Launcher is not installed. Run: bash scripts/studio.sh install"; ru="Task Studio Launcher не установлен. Выполните: bash scripts/studio.sh install" ;;
    err_not_installed_ps) en="Task Studio Launcher is not installed. Run: .\\scripts\\studio.cmd install"; ru="Task Studio Launcher не установлен. Выполните: .\\scripts\\studio.cmd install" ;;
    err_up_short) en="Failed to start containers."; ru="Не удалось запустить контейнеры." ;;
    err_compose_missing_file) en="Not found: %s. Run the launcher from the repository root."; ru="Не найдено: %s. Запустите лаунчер из корня репозитория." ;;
    err_no_env_stop) en="No .env file — there is nothing to stop."; ru="Нет файла .env — останавливать нечего." ;;
    err_still_running) en="Some containers are still running. Try again or check: docker compose ps"; ru="Часть контейнеров ещё работает. Повторите попытку или проверьте: docker compose ps" ;;
    err_no_env_install) en="No .env file — run Install first."; ru="Нет файла .env — сначала выполните установку." ;;
    err_stop_before_restart) en="Could not stop all containers before restart."; ru="Не удалось остановить все контейнеры перед перезапуском." ;;
    err_up_after_restart) en="Failed to start containers after restart."; ru="Не удалось запустить контейнеры после перезапуска." ;;
    err_ui_after_restart) en="Restart finished, but the web interface is not responding at %s."; ru="Перезапуск выполнен, но веб-интерфейс не отвечает: %s." ;;
    info_http_port_fallback) en="Port 80 is busy on loopback; the Task Studio web interface will use http://localhost:%s"; ru="Порт 80 на loopback занят; веб-интерфейс Task Studio: http://localhost:%s" ;;
    err_unknown_opt) en="Unknown option: %s"; ru="Неизвестный параметр: %s" ;;
    err_install_not_found) en="Task Studio Launcher installation was not found."; ru="Установка Task Studio Launcher не найдена." ;;
    err_uninstall_running) en="Cannot uninstall while containers are still running."; ru="Нельзя удалять, пока контейнеры ещё работают." ;;
    err_robocopy) en="robocopy was not found (required for a safe update on Windows)."; ru="robocopy не найден (нужен для безопасного обновления в Windows)." ;;
    err_update_dev) en="Self-update is only for the consumer install (%s). Developer trees are left untouched."; ru="Самообновление доступно только для пользовательской установки (%s). Дерево разработчика не изменяется." ;;
    err_update_check) en="Update check failed: %s"; ru="Проверка обновлений не удалась: %s" ;;
    err_stop_before_update) en="Stop the containers before updating."; ru="Остановите контейнеры перед обновлением." ;;
    err_curl) en="curl was not found."; ru="curl не найден." ;;
    err_tar) en="tar was not found."; ru="tar не найден." ;;
    err_download) en="Failed to download the update archive."; ru="Не удалось скачать архив обновления." ;;
    err_unpack) en="Failed to unpack the update archive."; ru="Не удалось распаковать архив обновления." ;;
    err_layout) en="The update archive has an unexpected layout."; ru="Неожиданная структура архива обновления." ;;
    err_fingerprint) en="Could not fingerprint the downloaded package."; ru="Не удалось посчитать отпечаток скачанного пакета." ;;
    err_sync) en="Failed to sync application files."; ru="Не удалось синхронизировать файлы приложения." ;;
    err_env_gone) en="Safety abort: .env disappeared during the update."; ru="Аварийная остановка: файл .env пропал во время обновления." ;;
    err_build_update) en="Docker image build failed after the update."; ru="Сборка образов Docker не удалась после обновления." ;;
    err_up_update) en="Failed to start containers after the update."; ru="Не удалось запустить контейнеры после обновления." ;;
    err_leave_root) en="Cannot leave %s in order to delete it."; ru="Нельзя выйти из %s, чтобы удалить эту папку." ;;
    upd_unknown) en="unknown error"; ru="неизвестная ошибка" ;;
    upd_summary) en="Update %s → %s"; ru="Обновление %s → %s" ;;
    upd_up_to_date) en="Up to date (%s)"; ru="Актуально (%s)" ;;
    upd_offline) en="Could not reach the version manifest (offline?)"; ru="Не удалось получить манифест версии (нет сети?)" ;;
    upd_invalid) en="Invalid version manifest"; ru="Некорректный манифест версии" ;;
    upd_unsupported) en="Developer tree — self-update is disabled (consumer install only)"; ru="Дерево разработчика — самообновление отключено (только пользовательская установка)" ;;
    upd_curl_missing) en="curl was not found"; ru="curl не найден" ;;
    usage_body) en="Usage:
  bash scripts/studio.sh              Interactive manager
  bash scripts/studio.sh install      First setup / rebuild
  bash scripts/studio.sh start        Start containers
  bash scripts/studio.sh open         Open the web interface
  bash scripts/studio.sh stop         Stop the stack
  bash scripts/studio.sh restart      Stop, then start again
  bash scripts/studio.sh uninstall    Remove the stack (add --purge to delete the folder)
  bash scripts/studio.sh update       Download the latest build and rebuild
  bash scripts/studio.sh help         Show this help

Menu items depend on stack state (not installed / stopped / running).
On open, the launcher checks a remote version file (about once per hour).
Update downloads a package, verifies checksums, and replaces application files.
User data (data/, .env) is never overwritten. Updates are never silent."; ru="Использование:
  bash scripts/studio.sh              Интерактивный менеджер
  bash scripts/studio.sh install      Первая установка / пересборка
  bash scripts/studio.sh start        Запуск контейнеров
  bash scripts/studio.sh open         Открыть веб-интерфейс
  bash scripts/studio.sh stop         Остановка стека
  bash scripts/studio.sh restart      Остановить и запустить снова
  bash scripts/studio.sh uninstall    Удаление стека (добавьте --purge, чтобы стереть папку)
  bash scripts/studio.sh update       Скачать обновление и пересобрать
  bash scripts/studio.sh help         Эта справка

Пункты меню зависят от состояния стека (не установлено / остановлено / запущено).
При открытии лаунчер проверяет удалённый файл версии (примерно раз в час).
Обновление скачивает пакет, сверяет контрольные суммы и заменяет файлы приложения.
Данные пользователя (data/, .env) не затираются. Обновление никогда не выполняется тихо." ;;
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

if [[ -z "${TS_UI_LANG}" ]]; then
  ts_detect_lang
fi
