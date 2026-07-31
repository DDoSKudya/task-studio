#Requires -Version 5.1
# Locale for Task Studio Launcher. Russian OS → Cyrillic; else English.
# Synced from scripts/lib/i18n.sh (Windows-specific help/usage overrides).
$script:TsUiLang = "en"

function Initialize-TsI18n {
  $script:TsUiLang = "en"
  try {
    $name = [System.Globalization.CultureInfo]::CurrentUICulture.TwoLetterISOLanguageName
    if ($name -eq "ru") { $script:TsUiLang = "ru" }
  } catch { }
  foreach ($var in @($env:LANG, $env:LC_ALL, $env:LC_MESSAGES)) {
    if ($var -and ($var -match "(?i)^ru([_.@]|$)")) { $script:TsUiLang = "ru"; break }
  }
}

function Get-TsText {
  param(
    [Parameter(Mandatory = $true)][string]$Key,
    [Parameter(ValueFromRemainingArguments = $true)]$FormatArgs
  )
  if (-not $script:TsUiLang) { Initialize-TsI18n }
  $en = $null; $ru = $null
  switch ($Key) {
    'app_title' {
      $en = 'Task Studio Launcher'; $ru = 'Task Studio Launcher'
    }
    'action_cancel' {
      $en = 'Cancel'; $ru = 'Отмена'
    }
    'action_delete' {
      $en = 'Delete'; $ru = 'Удалить'
    }
    'boot_downloading' {
      $en = 'Downloading Task Studio Launcher into %s …'; $ru = 'Скачивание Task Studio Launcher в %s …'
    }
    'boot_git_missing' {
      $en = 'git not found.'; $ru = 'git не найден.'
    }
    'boot_ps_fallback' {
      $en = '  You can still start: %s'; $ru = '  Можно запустить вручную: %s'
    }
    'boot_ps_git_missing' {
      $en = 'git not found. Install Git for Windows, then re-run: irm …/install.ps1 | iex'; $ru = 'git не найден. Установите Git for Windows и снова выполните: irm …/install.ps1 | iex'
    }
    'boot_ps_prepare' {
      $en = 'Preparing PowerShell execution and desktop shortcut…'; $ru = 'Подготовка PowerShell и ярлыка на рабочий стол…'
    }
    'boot_ps_shortcut_fail' {
      $en = 'Warning: desktop shortcut failed — %s'; $ru = 'Предупреждение: ярлык не создан — %s'
    }
    'boot_ps_studio_missing' {
      $en = 'studio.ps1 not found under %s\scripts'; $ru = 'studio.ps1 не найден в %s\scripts'
    }
    'boot_shortcut_warn' {
      $en = 'Warning: could not create desktop shortcut (you can still run: bash %s/scripts/studio.sh).'; $ru = 'Предупреждение: не удалось создать ярлык (можно запустить: bash %s/scripts/studio.sh).'
    }
    'boot_shortcuts' {
      $en = 'Installing console and desktop shortcut…'; $ru = 'Установка консоли и ярлыка на рабочий стол…'
    }
    'boot_starting' {
      $en = 'Starting Task Studio Launcher…'; $ru = 'Запуск Task Studio Launcher…'
    }
    'boot_starting_new_window' {
      $en = 'Opening Task Studio Launcher in a new window…'; $ru = 'Открытие Task Studio Launcher в новом окне…'
    }
    'boot_studio_missing' {
      $en = 'studio.sh not found under %s/scripts'; $ru = 'studio.sh не найден в %s/scripts'
    }
    'boot_updating' {
      $en = 'Updating existing install…'; $ru = 'Обновление существующей установки…'
    }
    'bye' {
      $en = 'Bye.'; $ru = 'Пока.'
    }
    'cmd_failed' {
      $en = 'Command failed (exit %s)'; $ru = 'Команда завершилась с ошибкой (код %s)'
    }
    'err_progress_empty_log' {
      $en = 'Command failed before writing a log (exit early). Often data/logs is not writable (Docker owns data/). Log path: %s'; $ru = 'Команда упала до записи лога. Часто data/logs недоступен для записи (каталог data/ создал Docker). Путь лога: %s'
    }
    'cmd_failed_short' {
      $en = 'Command failed'; $ru = 'Команда завершилась с ошибкой'
    }
    'confirm_continue' {
      $en = 'Continue?'; $ru = 'Продолжить?'
    }
    'confirm_purge' {
      $en = 'Also delete the install folder (launcher scripts included)?'; $ru = 'Также удалить папку установки (включая лаунчер)?'
    }
    'confirm_uninstall' {
      $en = 'Uninstall Task Studio? Containers and local data will be removed.'; $ru = 'Удалить Task Studio? Будут удалены контейнеры и локальные данные.'
    }
    'done_returning' {
      $en = 'Done. Returning in 5s…'; $ru = 'Готово. Возврат через 5 с…'
    }
    'enter_back' {
      $en = 'Enter = back'; $ru = 'Enter — назад'
    }
    'enter_continue' {
      $en = 'Enter = continue'; $ru = 'Enter = дальше'
    }
    'err_build' {
      $en = 'Docker build failed. Check Docker is running and disk space is available.'; $ru = 'Сборка Docker не удалась. Проверьте, что Docker запущен и есть место на диске.'
    }
    'err_build_short' {
      $en = 'Docker build failed.'; $ru = 'Сборка Docker не удалась.'
    }
    'err_build_update' {
      $en = 'Docker build failed after update.'; $ru = 'Сборка Docker не удалась после обновления.'
    }
    'err_buildkit' {
      $en = 'Docker Engine %s is too old. Task Studio needs Docker 20+ with BuildKit (cache mounts). Upgrade Docker Desktop / Engine.'; $ru = 'Docker Engine %s слишком старый. Нужен Docker 20+ с BuildKit (cache mounts). Обновите Docker Desktop / Engine.'
    }
    'err_compose_missing' {
      $en = 'Docker Compose v2 is required (command: docker compose). Update Docker Desktop or install the compose plugin.'; $ru = 'Нужен Docker Compose v2 (команда: docker compose). Обновите Docker Desktop или установите плагин compose.'
    }
    'err_compose_missing_file' {
      $en = 'Not found: %s. Run from the repository root.'; $ru = 'Не найдено: %s. Запустите из корня репозитория.'
    }
    'err_curl' {
      $en = 'curl not found.'; $ru = 'curl не найден.'
    }
    'err_docker_missing' {
      $en = 'Docker not found. Install Docker Desktop (macOS/Windows) or Docker Engine + Compose v2 (Linux), then start it and retry.'; $ru = 'Docker не найден. Установите Docker Desktop (macOS/Windows) или Docker Engine + Compose v2 (Linux), запустите его и повторите.'
    }
    'err_docker_stopped' {
      $en = 'Docker is installed but not running. Start Docker Desktop / the Docker daemon and wait until it is ready.'; $ru = 'Docker установлен, но не запущен. Запустите Docker Desktop / демон Docker и дождитесь готовности.'
    }
    'err_docker_desktop_engine' {
      $en = 'Docker Desktop engine is not running (named pipe missing). Open Docker Desktop, wait until it says Running / Engine running, then retry. WSL 2 backend must be enabled.'; $ru = 'Движок Docker Desktop не запущен (нет named pipe). Откройте Docker Desktop, дождитесь статуса Running, затем повторите. Нужен backend WSL 2.'
    }
    'err_docker_start_failed' {
      $en = 'Could not start Docker automatically. Start Docker Desktop / enable the docker service, wait until it is ready, then retry.'; $ru = 'Не удалось запустить Docker автоматически. Запустите Docker Desktop / службу docker, дождитесь готовности и повторите.'
    }
    'err_docker_unusable' {
      $en = 'Docker is installed but not usable. Start Docker Desktop / the Docker daemon and wait until it is ready. Detail: %s'; $ru = 'Docker установлен, но недоступен. Запустите Docker Desktop / демон Docker и дождитесь готовности. Подробности: %s'
    }
    'err_download' {
      $en = 'Failed to download update archive.'; $ru = 'Не удалось скачать архив обновления.'
    }
    'err_env_gone' {
      $en = 'Safety abort: .env disappeared during update.'; $ru = 'Аварийный стоп: .env пропал во время обновления.'
    }
    'err_fingerprint' {
      $en = 'Could not fingerprint downloaded package.'; $ru = 'Не удалось посчитать отпечаток скачанного пакета.'
    }
    'err_git' {
      $en = 'git not found.'; $ru = 'git не найден.'
    }
    'err_install_not_found' {
      $en = 'Task Studio Launcher install not found.'; $ru = 'Установка Task Studio Launcher не найдена.'
    }
    'err_layout' {
      $en = 'Update archive has unexpected layout.'; $ru = 'Неожиданная структура архива обновления.'
    }
    'err_leave_root' {
      $en = 'Cannot leave %s to delete it.'; $ru = 'Нельзя выйти из %s, чтобы удалить папку.'
    }
    'err_no_env_install' {
      $en = 'No .env file — run install first.'; $ru = 'Нет файла .env — сначала выполните установку.'
    }
    'err_no_env_stop' {
      $en = 'No .env file — nothing to stop.'; $ru = 'Нет файла .env — останавливать нечего.'
    }
    'err_not_installed' {
      $en = 'Installed Task Studio Launcher not found. Run: bash scripts/studio.sh install'; $ru = 'Установка Task Studio Launcher не найдена. Выполните: bash scripts/studio.sh install'
    }
    'err_not_installed_ps' {
      $en = 'Installed Task Studio Launcher not found. Run: .\scripts\studio.cmd install'; $ru = 'Установка Task Studio Launcher не найдена. Выполните: .\scripts\studio.cmd install'
    }
    'err_openssl' {
      $en = 'openssl or python3 required to generate secrets'; $ru = 'Для генерации секретов нужны openssl или python3'
    }
    'err_ram' {
      $en = 'Detected ≈%s GB RAM; minimum to start is %s GB (16 GB recommended).'; $ru = 'Обнаружено ≈%s ГБ ОЗУ; минимум для старта %s ГБ (рекомендуется 16 ГБ).'
    }
    'err_robocopy' {
      $en = 'robocopy not found (required for safe update on Windows).'; $ru = 'robocopy не найден (нужен для безопасного обновления в Windows).'
    }
    'err_robocopy_code' {
      $en = 'robocopy failed with code %s'; $ru = 'robocopy завершился с кодом %s'
    }
    'err_still_running' {
      $en = 'Some containers are still running. Try again or check: docker compose ps'; $ru = 'Часть контейнеров ещё работает. Повторите или проверьте: docker compose ps'
    }
    'err_stop_before_restart' {
      $en = 'Could not stop all containers before restart.'; $ru = 'Не удалось остановить все контейнеры перед перезапуском.'
    }
    'err_stop_before_update' {
      $en = 'Stop containers before updating.'; $ru = 'Остановите контейнеры перед обновлением.'
    }
    'err_sync' {
      $en = 'Failed to sync application files.'; $ru = 'Не удалось синхронизировать файлы приложения.'
    }
    'err_tar' {
      $en = 'tar not found.'; $ru = 'tar не найден.'
    }
    'err_ui' {
      $en = 'Containers started, but UI is not responding at %s'; $ru = 'Контейнеры запущены, но UI не отвечает: %s'
    }
    'err_ui_after_restart' {
      $en = 'Restarted, but the UI is not responding at %s.'; $ru = 'Перезапущено, но UI не отвечает: %s.'
    }
    'err_uninstall_running' {
      $en = 'Cannot uninstall while containers are still running.'; $ru = 'Нельзя удалять, пока контейнеры ещё работают.'
    }
    'err_unknown_opt' {
      $en = 'Unknown option: %s'; $ru = 'Неизвестный параметр: %s'
    }
    'err_unpack' {
      $en = 'Failed to unpack update archive.'; $ru = 'Не удалось распаковать архив обновления.'
    }
    'err_up' {
      $en = 'Failed to start containers (docker compose up).'; $ru = 'Не удалось запустить контейнеры (docker compose up).'
    }
    'err_up_after_restart' {
      $en = 'Failed to start containers after restart.'; $ru = 'Не удалось запустить контейнеры после перезапуска.'
    }
    'err_up_short' {
      $en = 'Failed to start containers.'; $ru = 'Не удалось запустить контейнеры.'
    }
    'err_up_update' {
      $en = 'Failed to start containers after update.'; $ru = 'Не удалось запустить контейнеры после обновления.'
    }
    'err_update_check' {
      $en = 'Update check failed: %s'; $ru = 'Проверка обновлений не удалась: %s'
    }
    'err_update_dev' {
      $en = 'Self-update is only for the consumer install (%s). Developer trees are left untouched.'; $ru = 'Самообновление только для пользовательской установки (%s). Дерево разработчика не трогаем.'
    }
    'help_line_install' {
      $en = 'studio.cmd install      Build and configure'; $ru = 'studio.cmd install      Сборка и настройка'
    }
    'help_line_menu' {
      $en = 'studio.cmd              Interactive manager'; $ru = 'studio.cmd              Интерактивный менеджер'
    }
    'help_line_restart' {
      $en = 'studio.cmd restart      Stop then start'; $ru = 'studio.cmd restart      Стоп, затем старт'
    }
    'help_line_start' {
      $en = 'studio.cmd start        Run app + open browser'; $ru = 'studio.cmd start        Запуск + браузер'
    }
    'help_line_stop' {
      $en = 'studio.cmd stop         Shut down containers'; $ru = 'studio.cmd stop         Остановка контейнеров'
    }
    'help_line_uninstall' {
      $en = 'studio.cmd uninstall    Remove stack (-Purge)'; $ru = 'studio.cmd uninstall    Удалить стек (-Purge)'
    }
    'help_line_update' {
      $en = 'studio.cmd update       Pull latest + rebuild'; $ru = 'studio.cmd update       Скачать обновление + пересборка'
    }
    'help_title' {
      $en = 'Help'; $ru = 'Справка'
    }
    'help_update_note1' {
      $en = 'On start, studio checks the remote version manifest (throttled).'; $ru = 'При старте studio проверяет удалённый манифест версии (с ограничением частоты).'
    }
    'help_update_note2' {
      $en = 'Update downloads an archive, compares checksums, replaces app files.'; $ru = 'Update скачивает архив, сверяет контрольные суммы, заменяет файлы приложения.'
    }
    'help_update_note3' {
      $en = 'User data is preserved: data/, .env, local compose overrides.'; $ru = 'Данные пользователя сохраняются: data/, .env, локальные compose-overrides.'
    }
    'info_cancelled' {
      $en = 'Cancelled.'; $ru = 'Отменено.'
    }
    'info_clone' {
      $en = 'Repository not found — cloning into %s …'; $ru = 'Репозиторий не найден — клонирование в %s …'
    }
    'info_console' {
      $en = 'Console: bash ./scripts/studio.sh'; $ru = 'Консоль: bash ./scripts/studio.sh'
    }
    'info_console_ps' {
      $en = 'Console: .\scripts\studio.cmd'; $ru = 'Консоль: .\scripts\studio.cmd'
    }
    'info_dir' {
      $en = 'Directory: %s'; $ru = 'Каталог: %s'
    }
    'info_env_created' {
      $en = 'Created .env from .env.example'; $ru = 'Создан .env из .env.example'
    }
    'info_jwt' {
      $en = 'Generated JWT_SECRET'; $ru = 'Сгенерирован JWT_SECRET'
    }
    'info_pull_model' {
      $en = 'Pulling Ollama model: %s (may take a while)…'; $ru = 'Загрузка модели Ollama: %s (может занять время)…'
    }
    'info_secrets_key' {
      $en = 'Generated SECRETS_MASTER_KEY'; $ru = 'Сгенерирован SECRETS_MASTER_KEY'
    }
    'info_ui' {
      $en = 'UI: %s'; $ru = 'UI: %s'
    }
    'menu_check_updates' {
      $en = 'Check for updates'; $ru = 'Проверить обновления'
    }
    'menu_footer' {
      $en = 'arrows move / Enter select / q quit'; $ru = 'стрелки — выбор / Enter — ок / q — выход'
    }
    'menu_footer_ps' {
      $en = 'arrows move / Enter select / Esc quit'; $ru = 'стрелки — выбор / Enter — ок / Esc — выход'
    }
    'menu_help' {
      $en = 'Help - show commands'; $ru = 'Справка — команды'
    }
    'menu_install' {
      $en = 'Install - first-time setup'; $ru = 'Установка — первый запуск'
    }
    'menu_install_repair' {
      $en = 'Install / repair - rebuild stack'; $ru = 'Установка / ремонт — пересборка стека'
    }
    'menu_heal' {
      $en = 'Heal - start missing / stopped containers'; $ru = 'Починить — поднять недостающие и остановленные'
    }
    'menu_quit' {
      $en = 'Quit'; $ru = 'Выход'
    }
    'menu_restart' {
      $en = 'Restart - stop then start'; $ru = 'Перезапуск — стоп, затем старт'
    }
    'menu_start' {
      $en = 'Start - run app and open browser'; $ru = 'Старт — запуск и открытие браузера'
    }
    'menu_stop' {
      $en = 'Stop - shut down containers'; $ru = 'Стоп — остановить контейнеры'
    }
    'menu_uninstall' {
      $en = 'Uninstall - remove containers and data'; $ru = 'Удаление — контейнеры и данные'
    }
    'menu_update' {
      $en = 'Update - download latest and rebuild'; $ru = 'Обновление — скачать и пересобрать'
    }
    'no' {
      $en = 'No'; $ru = 'Нет'
    }
    'press_enter_close' {
      $en = 'Press Enter to close…'; $ru = 'Нажмите Enter, чтобы закрыть…'
    }
    'press_enter_menu' {
      $en = 'Press Enter to return to the menu...'; $ru = 'Нажмите Enter, чтобы вернуться в меню…'
    }
    'prog_completed' {
      $en = 'Completed successfully'; $ru = 'Успешно завершено'
    }
    'prog_details' {
      $en = 'Log: %s'; $ru = 'Лог: %s'
    }
    'prog_details_ps' {
      $en = 'Log: %s'; $ru = 'Лог: %s'
    }
    'prog_log_hint' {
      $en = 'Full log: %s'; $ru = 'Полный лог: %s'
    }
    'prog_done' {
      $en = 'Done'; $ru = 'Готово'
    }
    'prog_error_label' {
      $en = 'Error'; $ru = 'Ошибка'
    }
    'prog_eta_done' {
      $en = 'done'; $ru = 'готово'
    }
    'prog_eta_failed' {
      $en = 'failed'; $ru = 'ошибка'
    }
    'prog_eta_finishing' {
      $en = 'finishing…'; $ru = 'завершение…'
    }
    'prog_eta_hm' {
      $en = '~ %sh %sm left'; $ru = '~ %s ч %s мин осталось'
    }
    'prog_eta_min' {
      $en = '~ %s min left'; $ru = '~ %s мин осталось'
    }
    'prog_eta_sec' {
      $en = '~ %ss left'; $ru = '~ %s с осталось'
    }
    'prog_failed' {
      $en = 'Failed'; $ru = 'Ошибка'
    }
    'prog_finished_ok' {
      $en = 'Finished successfully'; $ru = 'Успешно завершено'
    }
    'prog_footer_idle' {
      $en = 'progress / Enter when done'; $ru = 'прогресс / Enter — когда готово'
    }
    'prog_footer_return' {
      $en = 'Enter = back / auto in 5s'; $ru = 'Enter — назад / авто через 5 с'
    }
    'prog_footer_run' {
      $en = 'working… please wait'; $ru = 'работаю… подождите'
    }
    'prog_starting' {
      $en = 'Starting'; $ru = 'Старт'
    }
    'prog_unknown_error' {
      $en = 'Unknown error'; $ru = 'Неизвестная ошибка'
    }
    'prompt_default' {
      $en = 'What do you want to do?'; $ru = 'Что сделать?'
    }
    'prompt_missing' {
      $en = 'Not installed — what do you want to do?'; $ru = 'Не установлено — что сделать?'
    }
    'prompt_running' {
      $en = 'Running — what do you want to do?'; $ru = 'Запущено — что сделать?'
    }
    'prompt_stopped' {
      $en = 'Stopped — what do you want to do?'; $ru = 'Остановлено — что сделать?'
    }
    'prompt_update' {
      $en = 'Update available — what do you want to do?'; $ru = 'Доступно обновление — что сделать?'
    }
    'returning_footer' {
      $en = 'Returning in %ss / Enter = now'; $ru = 'Возврат через %s с / Enter = сразу'
    }
    'shortcut_blocked_hint' {
      $en = 'If the script is blocked, run from Terminal:'; $ru = 'Если скрипт заблокирован, запустите из Terminal:'
    }
    'shortcut_comment' {
      $en = 'Task Studio Launcher'; $ru = 'Task Studio Launcher'
    }
    'shortcut_fail_exit' {
      $en = 'Task Studio Launcher failed with exit code %s.'; $ru = 'Task Studio Launcher завершился с кодом %s.'
    }
    'shortcut_main' {
      $en = 'Task Studio Launcher'; $ru = 'Task Studio Launcher'
    }
    'shortcut_uninstall' {
      $en = 'Task Studio Launcher — Uninstall'; $ru = 'Task Studio Launcher — Удаление'
    }
    'shortcuts_created' {
      $en = 'Shortcuts: %s'; $ru = 'Ярлыки: %s'
    }
    'stage_apply' {
      $en = 'Replace app files'; $ru = 'Замена файлов приложения'
    }
    'stage_build' {
      $en = 'Build images'; $ru = 'Сборка образов'
    }
    'stage_check' {
      $en = 'Check version'; $ru = 'Проверка версии'
    }
    'stage_download' {
      $en = 'Download package'; $ru = 'Скачивание пакета'
    }
    'stage_files' {
      $en = 'Remove local data'; $ru = 'Удаление локальных данных'
    }
    'stage_finish' {
      $en = 'Finish'; $ru = 'Завершение'
    }
    'stage_health' {
      $en = 'Health check'; $ru = 'Проверка готовности'
    }
    'stage_model' {
      $en = 'AI model'; $ru = 'Модель ИИ'
    }
    'stage_prepare' {
      $en = 'Prepare'; $ru = 'Подготовка'
    }
    'stage_rebuild' {
      $en = 'Rebuild stack'; $ru = 'Пересборка стека'
    }
    'stage_remove' {
      $en = 'Remove volumes and images'; $ru = 'Удаление томов и образов'
    }
    'stage_start' {
      $en = 'Start containers'; $ru = 'Запуск контейнеров'
    }
    'stage_stop' {
      $en = 'Stop containers'; $ru = 'Остановка контейнеров'
    }
    'stage_verify' {
      $en = 'Compare checksums'; $ru = 'Сверка контрольных сумм'
    }
    'status_already_stopped' {
      $en = 'Stack already stopped'; $ru = 'Стек уже остановлен'
    }
    'status_build_slow' {
      $en = 'Building container images (first run is slow)'; $ru = 'Сборка образов контейнеров (первый запуск долгий)'
    }
    'status_check_docker' {
      $en = 'Checking Docker and environment'; $ru = 'Проверка Docker и окружения'
    }
    'status_docker_starting' {
      $en = 'Docker is not ready — starting it…'; $ru = 'Docker не готов — запускаю…'
    }
    'status_docker_waiting' {
      $en = 'Waiting for Docker… %ss / %ss'; $ru = 'Ожидание Docker… %s с / %s с'
    }
    'status_starting_infra' {
      $en = 'Starting databases and brokers…'; $ru = 'Запуск баз и брокеров…'
    }
    'status_starting_catalog' {
      $en = 'Starting catalog service…'; $ru = 'Запуск сервиса catalog…'
    }
    'status_check_ui' {
      $en = 'Checking UI (%s)'; $ru = 'Проверка UI (%s)'
    }
    'status_checking_ui_plain' {
      $en = 'Checking UI'; $ru = 'Проверка UI'
    }
    'status_cleanup' {
      $en = 'Cleanup'; $ru = 'Очистка'
    }
    'status_compare_hash' {
      $en = 'Comparing content checksums (user data excluded)'; $ru = 'Сравнение контрольных сумм (без данных пользователя)'
    }
    'status_creating_shortcuts' {
      $en = 'Creating desktop shortcuts'; $ru = 'Создание ярлыков на рабочем столе'
    }
    'status_deleting_root' {
      $en = 'Deleting %s'; $ru = 'Удаление %s'
    }
    'status_delete_scheduled' {
      $en = 'Folder delete scheduled (separate process): %s'; $ru = 'Удаление папки запланировано (отдельный процесс): %s'
    }
    'status_downloading_ver' {
      $en = 'Downloading %s'; $ru = 'Скачивание %s'
    }
    'status_ensure_repo' {
      $en = 'Ensuring repository and .env'; $ru = 'Проверка репозитория и .env'
    }
    'status_ensure_stopped' {
      $en = 'Ensuring all containers are stopped'; $ru = 'Остановка всех контейнеров'
    }
    'status_hash_same' {
      $en = 'Checksum unchanged — only version stamp'; $ru = 'Контрольная сумма та же — только метка версии'
    }
    'status_locate' {
      $en = 'Locating install and checking Docker'; $ru = 'Поиск установки и проверка Docker'
    }
    'status_locate_short' {
      $en = 'Locating install'; $ru = 'Поиск установки'
    }
    'status_no_env' {
      $en = 'No .env yet — use Install from the menu'; $ru = 'Ещё нет .env — выберите Установку в меню'
    }
    'status_pull_model' {
      $en = 'Pulling Ollama model'; $ru = 'Загрузка модели Ollama'
    }
    'status_purge_skip' {
      $en = '--purge skipped — path is not %s'; $ru = '--purge пропущен — путь не %s'
    }
    'status_ram_power' {
      $en = 'RAM ≈%s GB — power_saving mode'; $ru = 'ОЗУ ≈%s ГБ — режим power_saving'
    }
    'status_build_parallel' {
      $en = 'Compose parallel builds limited to %s (RAM-safe)'; $ru = 'Параллельная сборка Compose ограничена до %s (бережём ОЗУ)'
    }
    'status_read_remote' {
      $en = 'Reading remote version'; $ru = 'Чтение удалённой версии'
    }
    'status_rebuild' {
      $en = 'Rebuilding and starting stack'; $ru = 'Пересборка и запуск стека'
    }
    'status_remove_files' {
      $en = 'Removing shortcuts, data/, .env'; $ru = 'Удаление ярлыков, data/, .env'
    }
    'status_remove_vol' {
      $en = 'Removing volumes and local images'; $ru = 'Удаление томов и локальных образов'
    }
    'status_removed_data' {
      $en = 'Removed data/'; $ru = 'Удалён data/'
    }
    'status_removed_env' {
      $en = 'Removed .env'; $ru = 'Удалён .env'
    }
    'status_replace_files' {
      $en = 'Replacing app files (preserving data/ and .env)'; $ru = 'Замена файлов приложения (data/ и .env сохраняются)'
    }
    'status_repo_kept' {
      $en = 'Install folder kept (launcher scripts remain).'; $ru = 'Папка установки сохранена (лаунчер остаётся).'
    }
    'status_shortcuts' {
      $en = 'Shortcuts and permissions'; $ru = 'Ярлыки и права'
    }
    'status_shortcuts_skip' {
      $en = 'Shortcuts skipped (optional)'; $ru = 'Ярлыки пропущены (необязательно)'
    }
    'status_skip_metrics' {
      $en = 'Skipping host-metrics (Docker Desktop / non-Linux)'; $ru = 'Пропуск host-metrics (Docker Desktop / не Linux)'
    }
    'status_skip_metrics_short' {
      $en = 'Skipping host-metrics profile'; $ru = 'Пропуск профиля host-metrics'
    }
    'status_starting_containers' {
      $en = 'Starting containers'; $ru = 'Запуск контейнеров'
    }
    'status_starting_ts' {
      $en = 'Starting Task Studio'; $ru = 'Запуск Task Studio'
    }
    'status_stop_before_update' {
      $en = 'Stopping containers before update'; $ru = 'Остановка контейнеров перед обновлением'
    }
    'status_stopping' {
      $en = 'Stopping containers'; $ru = 'Остановка контейнеров'
    }
    'status_ui_ok' {
      $en = 'UI is responding'; $ru = 'UI отвечает'
    }
    'status_up_to_date' {
      $en = 'Already up to date (%s)'; $ru = 'Уже актуально (%s)'
    }
    'status_waiting_ui' {
      $en = 'Waiting for UI at %s'; $ru = 'Ожидание UI: %s'
    }
    'title_install' {
      $en = 'Install'; $ru = 'Установка'
    }
    'title_restart' {
      $en = 'Restart'; $ru = 'Перезапуск'
    }
    'title_start' {
      $en = 'Start'; $ru = 'Старт'
    }
    'title_stop' {
      $en = 'Stop'; $ru = 'Стоп'
    }
    'title_uninstall' {
      $en = 'Uninstall'; $ru = 'Удаление'
    }
    'title_update' {
      $en = 'Update'; $ru = 'Обновление'
    }
    'type_yes_continue' {
      $en = 'Type YES to continue:'; $ru = 'Введите YES для продолжения:'
    }
    'type_yes_hint' {
      $en = 'Type YES (uppercase) to confirm. Anything else cancels.'; $ru = 'Введите YES (заглавными), чтобы подтвердить. Любой другой ввод — отмена.'
    }
    'unknown_choice' {
      $en = 'Unknown choice: %s'; $ru = 'Неизвестный выбор: %s'
    }
    'unknown_command' {
      $en = 'Unknown command: %s'; $ru = 'Неизвестная команда: %s'
    }
    'upd_curl_missing' {
      $en = 'curl not found'; $ru = 'curl не найден'
    }
    'upd_invalid' {
      $en = 'Invalid version manifest'; $ru = 'Некорректный манифест версии'
    }
    'upd_offline' {
      $en = 'Could not reach version manifest (offline?)'; $ru = 'Не удалось получить манифест версии (нет сети?)'
    }
    'upd_unknown' {
      $en = 'unknown error'; $ru = 'неизвестная ошибка'
    }
    'upd_summary' {
      $en = 'Update %s → %s'; $ru = 'Обновление %s → %s'
    }
    'upd_unsupported' {
      $en = 'Developer tree — self-update disabled (consumer install only)'; $ru = 'Дерево разработчика — самообновление отключено (только пользовательская установка)'
    }
    'upd_up_to_date' {
      $en = 'Up to date (%s)'; $ru = 'Актуально (%s)'
    }
    'usage_body' {
      $en = @"
Usage:
  .\scripts\studio.cmd              Interactive dialog manager
  .\scripts\studio.cmd install      First-time setup / rebuild
  .\scripts\studio.cmd start        Start stack + open UI
  .\scripts\studio.cmd open         Open web UI in browser
  .\scripts\studio.cmd stop         Stop stack
  .\scripts\studio.cmd restart      Stop then start
  .\scripts\studio.cmd uninstall    Remove stack (add -Purge to delete folder)
  .\scripts\studio.cmd update       Pull latest code and rebuild
  .\scripts\studio.cmd help         This help

Menu actions depend on stack state (not installed / stopped / running).
On open, studio checks a remote version file (about once per hour).
Update downloads a package, compares checksums, and replaces app files.
User data (data/, .env) is never overwritten. Update is never silent.
"@
      $ru = @"
Использование:
  .\scripts\studio.cmd              Интерактивный менеджер
  .\scripts\studio.cmd install      Первая установка / пересборка
  .\scripts\studio.cmd start        Запуск стека + UI
  .\scripts\studio.cmd open         Открыть web UI в браузере
  .\scripts\studio.cmd stop         Остановка
  .\scripts\studio.cmd restart      Стоп, затем старт
  .\scripts\studio.cmd uninstall    Удаление стека (добавьте -Purge, чтобы стереть папку)
  .\scripts\studio.cmd update       Скачать обновление и пересобрать
  .\scripts\studio.cmd help         Эта справка

Пункты меню зависят от состояния стека (не установлено / остановлено / запущено).
При открытии studio проверяет удалённый файл версии (примерно раз в час).
Update скачивает пакет, сверяет контрольные суммы и заменяет файлы приложения.
Данные пользователя (data/, .env) не затираются. Обновление никогда не тихое.
"@
    }
    'usage_header' {
      $en = 'Task Studio Launcher'; $ru = 'Task Studio Launcher'
    }
    'warn_compose_down' {
      $en = 'compose down reported an error — %s'; $ru = 'compose down сообщил об ошибке — %s'
    }
    'warn_desktop_unwritable' {
      $en = 'Cannot write to desktop directory: %s'; $ru = 'Нельзя писать в папку рабочего стола: %s'
    }
    'warn_model_pull' {
      $en = 'Could not pull the model now. Later: docker compose -f %s --env-file .env --profile full exec ollama ollama pull %s'; $ru = 'Не удалось скачать модель сейчас. Позже: docker compose -f %s --env-file .env --profile full exec ollama ollama pull %s'
    }
    'warn_model_pull_short' {
      $en = 'Could not pull the model now.'; $ru = 'Не удалось скачать модель сейчас.'
    }
    'warn_path_windows' {
      $en = 'Install is on a Windows drive (%s). Prefer WSL home (~/task-studio) for Docker data dirs — NTFS bind mounts often break Postgres/ClickHouse.'; $ru = 'Установка на диске Windows (%s). Для каталогов data/ лучше WSL (~/task-studio) — bind-mount NTFS часто ломает Postgres/ClickHouse.'
    }
    'warn_path_wsl_mnt' {
      $en = 'Install path is on /mnt/... (%s). Prefer a Linux filesystem home (e.g. ~/task-studio) — NTFS mounts often break Postgres/ClickHouse permissions.'; $ru = 'Путь установки на /mnt/... (%s). Лучше домашний каталог Linux (например ~/task-studio) — монтирование NTFS часто ломает права Postgres/ClickHouse.'
    }
    'warn_purge' {
      $en = 'The install folder will also be deleted (including the launcher): %s'; $ru = 'Также будет удалена папка установки (включая лаунчер): %s'
    }
    'warn_purge_launcher' {
      $en = 'Consumer install: the whole folder will be removed after this process exits: %s'; $ru = 'Пользовательская установка: после выхода будет удалена вся папка: %s'
    }
    'warn_purge_ps' {
      $en = 'The install folder will also be deleted (including the launcher): %s'; $ru = 'Также будет удалена папка установки (включая лаунчер): %s'
    }
    'warn_purge_skip_got' {
      $en = '-Purge skipped — path is not %s (got %s).'; $ru = '-Purge пропущен — путь не %s (сейчас %s).'
    }
    'warn_refresh_shortcuts' {
      $en = 'Could not refresh shortcuts — %s'; $ru = 'Не удалось обновить ярлыки — %s'
    }
    'warn_shortcuts' {
      $en = 'Could not create shortcuts — %s'; $ru = 'Не удалось создать ярлыки — %s'
    }
    'warn_ui_after_update' {
      $en = 'Updated, but UI is not responding yet at %s'; $ru = 'Обновлено, но UI пока не отвечает: %s'
    }
    'warn_ui_unreachable' {
      $en = 'UI is not responding at %s. Use Heal, Restart, or Install/repair.'; $ru = 'UI не отвечает: %s. Используйте Починить, Перезапуск или Установка/ремонт.'
    }
    'warn_uninstall' {
      $en = 'This removes containers, volumes, local images, data/, shortcuts, and .env.'; $ru = 'Будут удалены контейнеры, тома, локальные образы, data/, ярлыки и .env.'
    }
    'yes' {
      $en = 'Yes'; $ru = 'Да'
    }
    'help_line_open' {
      $en = 'studio.cmd open         Open web UI in browser'; $ru = 'studio.cmd open         Открыть web UI в браузере'
    }
    'info_open_manual' {
      $en = 'Open in browser: %s'; $ru = 'Откройте в браузере: %s'
    }
    'info_opened_ui' {
      $en = 'Opened %s'; $ru = 'Открыто: %s'
    }
    'menu_open' {
      $en = 'Open - launch web UI in browser'; $ru = 'Открыть — web-интерфейс в браузере'
    }
    'title_open' {
      $en = 'Open'; $ru = 'Открыть'
    }
    'prog_spinner_frames' {
      $en = '|/-\'; $ru = '|/-\'
    }
    default { $en = $Key; $ru = $Key }
  }
  $text = if ($script:TsUiLang -eq "ru") { $ru } else { $en }
  if ($FormatArgs -and $FormatArgs.Count -gt 0) {
    foreach ($a in $FormatArgs) {
      $p = $text.IndexOf('%s')
      if ($p -lt 0) { $p = $text.IndexOf('%d') }
      if ($p -lt 0) { break }
      $text = $text.Substring(0, $p) + [string]$a + $text.Substring($p + 2)
    }
  }
  return $text
}

Initialize-TsI18n

