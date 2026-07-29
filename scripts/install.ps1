#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$RepoHttps = if ($env:TASK_STUDIO_REPO_HTTPS) { $env:TASK_STUDIO_REPO_HTTPS } else { "https://github.com/DDoSKudya/task-studio.git" }
$RepoBranch = if ($env:TASK_STUDIO_BRANCH) { $env:TASK_STUDIO_BRANCH } else { "develop" }
$InstallDir = if ($env:TASK_STUDIO_DIR) { $env:TASK_STUDIO_DIR } else { Join-Path $HOME "task-studio" }
$ComposeFile = "deploy/docker-compose.yml"
$MinRamGb = if ($env:TASK_STUDIO_MIN_RAM_GB) { [int]$env:TASK_STUDIO_MIN_RAM_GB } else { 8 }
$OllamaModel = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "qwen2.5:3b" }

function Write-Log([string]$Message) { Write-Host $Message }

function Assert-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Не найдена команда «$Name». Установите Docker Desktop и повторите."
  }
}

function Get-RamGb {
  try {
    $cs = Get-CimInstance Win32_ComputerSystem
    return [int][math]::Floor($cs.TotalPhysicalMemory / 1GB)
  } catch {
    return 0
  }
}

function Ensure-Repo {
  if ((Test-Path $ComposeFile) -and (Test-Path ".env.example")) {
    return (Get-Location).Path
  }
  $candidate = Join-Path $InstallDir $ComposeFile
  if (Test-Path $candidate) {
    Set-Location $InstallDir
    return (Get-Location).Path
  }
  Write-Log "Репозиторий не найден — клонирую в $InstallDir …"
  Assert-Command git
  $parent = Split-Path -Parent $InstallDir
  if ($parent -and -not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
  git clone --branch $RepoBranch --depth 1 $RepoHttps $InstallDir
  Set-Location $InstallDir
  return (Get-Location).Path
}

function Get-EnvValue([string]$Name) {
  $line = Get-Content ".env" -ErrorAction SilentlyContinue | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
  if (-not $line) { return "" }
  return ($line -split "=", 2)[1].Trim().Trim('"').Trim("'")
}

function Set-EnvValue([string]$Name, [string]$Value) {
  $lines = @(Get-Content ".env")
  $found = $false
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "^$Name=") {
      $lines[$i] = "$Name=$Value"
      $found = $true
      break
    }
  }
  if (-not $found) { $lines += "$Name=$Value" }
  Set-Content -Path ".env" -Value $lines -Encoding utf8
}

function New-MasterKey {
  $bytes = New-Object byte[] 32
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  return [Convert]::ToBase64String($bytes)
}

function New-JwtSecret {
  $bytes = New-Object byte[] 48
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  return [Convert]::ToBase64String($bytes)
}

function Test-MasterKey([string]$Raw) {
  if (-not $Raw -or $Raw.ToLower().Contains("change-me")) { return $false }
  try {
    $decoded = [Convert]::FromBase64String($Raw)
    return $decoded.Length -eq 32
  } catch {
    return $false
  }
}

function Ensure-Env {
  if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Log "Создан файл .env из .env.example"
  }

  $key = Get-EnvValue "SECRETS_MASTER_KEY"
  if (-not (Test-MasterKey $key)) {
    Set-EnvValue "SECRETS_MASTER_KEY" (New-MasterKey)
    Write-Log "Сгенерирован SECRETS_MASTER_KEY"
  }

  $jwt = Get-EnvValue "JWT_SECRET"
  if (-not $jwt -or $jwt.ToLower().Contains("change-me") -or $jwt.Length -lt 16) {
    Set-EnvValue "JWT_SECRET" (New-JwtSecret)
    Write-Log "Сгенерирован JWT_SECRET"
  }

  $model = Get-EnvValue "OLLAMA_MODEL"
  if (-not $model -or $model -eq "llama3.2") {
    Set-EnvValue "OLLAMA_MODEL" $OllamaModel
  }
}

function Prepare-Dirs {
  $dirs = @(
    "data/postgres", "data/redis", "data/rabbitmq", "data/packs",
    "data/meilisearch", "data/clickhouse", "data/minio", "data/ollama",
    "data/grafana", "data/prometheus", "data/piston/packages"
  )
  foreach ($d in $dirs) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
  }
}

Assert-Command docker
try { docker info | Out-Null } catch { throw "Docker не запущен. Откройте Docker Desktop и дождитесь готовности." }
try { docker compose version | Out-Null } catch { throw "Нужен Docker Compose v2." }

$ram = Get-RamGb
if ($ram -gt 0 -and $ram -lt $MinRamGb) {
  throw "Обнаружено ≈${ram} ГБ RAM, минимум — ${MinRamGb} ГБ (рекомендуется 16 ГБ)."
}
if ($ram -gt 0 -and $ram -lt 16) {
  $env:ORCHESTRATOR_MODE = if ($env:ORCHESTRATOR_MODE) { $env:ORCHESTRATOR_MODE } else { "power_saving" }
  Write-Log "RAM ≈${ram} ГБ — режим ORCHESTRATOR_MODE=power_saving."
}

$root = Ensure-Repo
Set-Location $root
Ensure-Env
Prepare-Dirs

$mode = if ($env:ORCHESTRATOR_MODE) { $env:ORCHESTRATOR_MODE } else { "balancing" }
$profileArgs = @("--profile", "full")
if ($mode -ne "power_saving") { $profileArgs += @("--profile", "editor") }

$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"

Write-Log "Собираю и запускаю контейнеры (первый запуск долгий)…"
docker compose -f $ComposeFile --env-file .env @profileArgs build
docker compose -f $ComposeFile --env-file .env @profileArgs up -d --remove-orphans

Write-Log "Жду готовности http://localhost …"
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
  try {
    Invoke-WebRequest -Uri "http://127.0.0.1" -UseBasicParsing -TimeoutSec 3 | Out-Null
    $ready = $true
    break
  } catch {
    Start-Sleep -Seconds 5
  }
}
if ($ready) { Write-Log "Стек отвечает на http://localhost" } else { Write-Log "Предупреждение: http://localhost пока не отвечает." }

$modelLine = (Get-Content .env | Where-Object { $_ -match '^OLLAMA_MODEL=' } | Select-Object -First 1)
$model = if ($modelLine) { ($modelLine -split '=', 2)[1].Trim() } else { $OllamaModel }
Write-Log "Загружаю модель Ollama: $model …"
try {
  docker compose -f $ComposeFile --env-file .env --profile full exec -T ollama ollama pull $model
} catch {
  Write-Log "Предупреждение: не удалось скачать модель сейчас."
}

Write-Log ""
Write-Log "Готово."
Write-Log "  Каталог:  $root"
Write-Log "  UI:        http://localhost"
Write-Log "  Остановка: .\scripts\stop.ps1"
Write-Log "  Зарегистрируйте пользователя на странице входа."
