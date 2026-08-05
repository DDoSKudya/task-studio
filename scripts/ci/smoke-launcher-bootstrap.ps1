#Requires -Version 5.1
param()

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$work = Join-Path ([System.IO.Path]::GetTempPath()) ("task-studio-bootstrap-" + [guid]::NewGuid().ToString())
$archive = Join-Path $work "src.zip"
$bootstrap = Join-Path $work "install.ps1"
$installDir = Join-Path $work "install"
$payloadDir = Join-Path $work "task-studio-smoke"

New-Item -ItemType Directory -Path $work -Force | Out-Null
try {
  New-Item -ItemType Directory -Path $payloadDir -Force | Out-Null
  foreach ($rel in (git -C $Root ls-files)) {
    $src = Join-Path $Root $rel
    $dst = Join-Path $payloadDir $rel
    $parent = Split-Path -Parent $dst
    if ($parent -and -not (Test-Path $parent)) {
      New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    Copy-Item $src $dst
  }
  Compress-Archive -Path $payloadDir -DestinationPath $archive
  Copy-Item (Join-Path $Root "scripts\install.ps1") $bootstrap

  $env:TASK_STUDIO_ARCHIVE_URL_ZIP = ([System.Uri]$archive).AbsoluteUri
  $env:TASK_STUDIO_DIR = $installDir
  $env:TASK_STUDIO_NO_PAUSE = "1"
  Push-Location $work
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    # Native stderr must not trip Stop; check exit code explicitly.
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
      -Command "& '$bootstrap' help" `
      2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
      throw "bootstrap install.ps1 help exited with code $LASTEXITCODE"
    }
  } finally {
    $ErrorActionPreference = $prevEap
    Pop-Location
  }

  if (-not (Test-Path (Join-Path $installDir "scripts\studio.ps1"))) {
    throw "bootstrap did not create scripts\studio.ps1"
  }
  if (-not (Test-Path (Join-Path $installDir "studio-version.json"))) {
    throw "bootstrap did not create studio-version.json"
  }
  if (-not (Test-Path (Join-Path $installDir ".studio-consumer"))) {
    throw "bootstrap did not create .studio-consumer"
  }
  if (-not (Test-Path (Join-Path $installDir ".studio-state.json"))) {
    throw "bootstrap did not create .studio-state.json"
  }

  $state = Get-Content -Raw (Join-Path $installDir ".studio-state.json") | ConvertFrom-Json
  if (-not $state.version) {
    throw "bootstrap state is missing version"
  }

  Write-Host "smoke-launcher-bootstrap.ps1: OK"
} finally {
  Remove-Item Env:TASK_STUDIO_ARCHIVE_URL_ZIP -ErrorAction SilentlyContinue
  Remove-Item Env:TASK_STUDIO_DIR -ErrorAction SilentlyContinue
  Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
