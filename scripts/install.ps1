#Requires -Version 5.1
# Public bootstrap — URL must stay stable (README / screenshot).
#
# Typical Windows entry (runs in memory — ExecutionPolicy does not block irm|iex):
#   irm https://raw.githubusercontent.com/DDoSKudya/task-studio/develop/scripts/install.ps1 | iex
#
# Then: download archive → unlock scripts → set CurrentUser policy if possible →
# desktop shortcut (studio.cmd + Bypass) → remove local install.* → start studio.
param([Parameter(ValueFromRemainingArguments = $true)]$Rest)

$ErrorActionPreference = "Stop"
$RepoBranch = if ($env:TASK_STUDIO_BRANCH) { $env:TASK_STUDIO_BRANCH } else { "develop" }
$ArchiveUrl = if ($env:TASK_STUDIO_ARCHIVE_URL_ZIP) { $env:TASK_STUDIO_ARCHIVE_URL_ZIP } else { "https://codeload.github.com/DDoSKudya/task-studio/zip/refs/heads/$RepoBranch" }
$InstallDir = if ($env:TASK_STUDIO_DIR) { $env:TASK_STUDIO_DIR } else { Join-Path $HOME "task-studio" }

# Locale: Russian OS → Cyrillic; otherwise English (no switches).
$script:TsUiLang = "en"
try {
  if ([System.Globalization.CultureInfo]::CurrentUICulture.TwoLetterISOLanguageName -eq "ru") {
    $script:TsUiLang = "ru"
  }
} catch { }
foreach ($var in @($env:LANG, $env:LC_ALL, $env:LC_MESSAGES)) {
  if ($var -and ($var -match "(?i)^ru([_.@]|$)")) { $script:TsUiLang = "ru"; break }
}

function Boot-TsText([string]$Key, [string]$En, [string]$Ru) {
  if ($script:TsUiLang -eq "ru") { return $Ru }
  return $En
}

function Convert-TsPsTreeToUtf8Bom([string]$Root) {
  $utf8Bom = New-Object System.Text.UTF8Encoding $true
  $paths = @(
    (Join-Path $Root "scripts\studio.ps1")
  ) + (Get-ChildItem -Path (Join-Path $Root "scripts\lib") -Filter "*.ps1" -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
  foreach ($path in ($paths | Select-Object -Unique)) {
    if (-not (Test-Path $path)) { continue }
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    [System.IO.File]::WriteAllText($path, $text, $utf8Bom)
  }
}

function Get-TsInstallRoot {
  if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "studio.ps1"))) {
    return (Split-Path -Parent $PSScriptRoot)
  }
  if ((Test-Path "deploy\docker-compose.yml") -and (Test-Path "scripts\studio.ps1")) {
    return (Get-Location).Path
  }
  $candidate = Join-Path $InstallDir "scripts\studio.ps1"
  if (Test-Path $candidate) {
    return (Resolve-Path $InstallDir).Path
  }
  return $null
}

function Install-TsArchive {
  Write-Host (Boot-TsText "dl" "Downloading Task Studio Launcher into $InstallDir …" "Скачивание Task Studio Launcher в $InstallDir …")
  $parent = Split-Path -Parent $InstallDir
  if ($parent -and -not (Test-Path $parent)) {
    New-Item -ItemType Directory -Path $parent | Out-Null
  }
  if (Test-Path $InstallDir) {
    Write-Host (Boot-TsText "upd" "Updating existing install…" "Обновление существующей установки…")
  }
  $work = Join-Path ([System.IO.Path]::GetTempPath()) ("task-studio-bootstrap-" + [guid]::NewGuid().ToString())
  $zipPath = Join-Path $work "src.zip"
  $extract = Join-Path $work "extract"
  New-Item -ItemType Directory -Path $extract -Force | Out-Null
  try {
    Invoke-WebRequest -Uri $ArchiveUrl -OutFile $zipPath -UseBasicParsing -TimeoutSec 600
    Expand-Archive -Path $zipPath -DestinationPath $extract -Force
    $payload = Get-ChildItem -Path $extract -Directory | Select-Object -First 1
    if (-not $payload -or -not (Test-Path (Join-Path $payload.FullName "scripts\studio.ps1"))) {
      throw "Downloaded archive has unexpected layout."
    }
    if (Test-Path $InstallDir) {
      Remove-Item -Recurse -Force $InstallDir
    }
    Move-Item -Path $payload.FullName -Destination $InstallDir
  } finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
  }
  return (Resolve-Path $InstallDir).Path
}

function Test-TsConsumerInstallDir([string]$Root) {
  $want = $InstallDir
  if (Test-Path $InstallDir) {
    $want = (Resolve-Path $InstallDir).Path
  }
  return ($Root -eq $want)
}

function Remove-TsBootstrapScripts([string]$Root) {
  if (-not (Test-TsConsumerInstallDir $Root)) { return }
  foreach ($name in @("install.sh", "install.ps1")) {
    $path = Join-Path $Root "scripts\$name"
    if (Test-Path $path) {
      Remove-Item -Force $path -ErrorAction SilentlyContinue
    }
  }
}

try {
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force -ErrorAction SilentlyContinue
} catch { }

$root = Get-TsInstallRoot
if (-not $root) {
  $root = Install-TsArchive
}

$studioPs1 = Join-Path $root "scripts\studio.ps1"
if (-not (Test-Path $studioPs1)) {
  throw (Boot-TsText "miss" "studio.ps1 not found under $root\scripts" "studio.ps1 не найден в $root\scripts")
}

Convert-TsPsTreeToUtf8Bom $root
Set-Location $root
$i18nPath = Join-Path $root "scripts\lib\I18n.ps1"
if (Test-Path $i18nPath) {
  . $i18nPath
}
. (Join-Path $root "scripts\lib\DesktopShortcuts.ps1")

if (Get-Command Get-TsText -ErrorAction SilentlyContinue) {
  Write-Host (Get-TsText boot_ps_prepare)
} else {
  Write-Host (Boot-TsText "prep" "Preparing PowerShell execution and desktop shortcut…" "Подготовка PowerShell и ярлыка на рабочий стол…")
}
try {
  Install-TaskStudioDesktopShortcuts -Root $root
} catch {
  $msg = $_.Exception.Message
  if (Get-Command Get-TsText -ErrorAction SilentlyContinue) {
    Write-Host (Get-TsText boot_ps_shortcut_fail $msg)
  } else {
    Write-Host (Boot-TsText "warn" "Warning: desktop shortcut failed — $msg" "Предупреждение: ярлык не создан — $msg")
  }
  $fallback = Join-Path $root "scripts\studio.cmd"
  if (Get-Command Get-TsText -ErrorAction SilentlyContinue) {
    Write-Host (Get-TsText boot_ps_fallback $fallback)
  } else {
    Write-Host (Boot-TsText "fb" "  You can still start: $fallback" "  Можно запустить вручную: $fallback")
  }
}

Remove-TsBootstrapScripts -Root $root

$installDefault = if ($env:TASK_STUDIO_DIR) { $env:TASK_STUDIO_DIR } else { Join-Path $HOME "task-studio" }
$resolvedDefault = $null
if (Test-Path $installDefault) { $resolvedDefault = (Resolve-Path $installDefault).Path }
if ($root -eq $installDefault -or ($resolvedDefault -and $root -eq $resolvedDefault)) {
  New-Item -ItemType File -Path (Join-Path $root ".studio-consumer") -Force | Out-Null
  $verFile = Join-Path $root "studio-version.json"
  if (Test-Path $verFile) {
    try {
      $ver = (Get-Content -Raw $verFile | ConvertFrom-Json).version
      if ($ver) {
        $payload = (@{ version = [string]$ver; content_sha256 = "" } | ConvertTo-Json) + "`n"
        $enc = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText((Join-Path $root ".studio-state.json"), $payload, $enc)
      }
    } catch { }
  }
}

if (Get-Command Get-TsText -ErrorAction SilentlyContinue) {
  Write-Host (Get-TsText boot_starting)
} else {
  Write-Host (Boot-TsText "start" "Starting Task Studio Launcher…" "Запуск Task Studio Launcher…")
}
$code = Start-TsStudioConsole -Root $root -Arguments $Rest
exit $code
