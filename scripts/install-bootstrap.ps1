

$ErrorActionPreference = "Stop"

$branch = if ($env:TASK_STUDIO_BRANCH) { $env:TASK_STUDIO_BRANCH } else { "develop" }
$base = "https://raw.githubusercontent.com/DDoSKudya/task-studio/$branch/scripts"
$dest = Join-Path $env:TEMP "task-studio-install.ps1"

if ($env:TASK_STUDIO_INSTALL_SCRIPT -and (Test-Path $env:TASK_STUDIO_INSTALL_SCRIPT)) {
  $dest = (Resolve-Path $env:TASK_STUDIO_INSTALL_SCRIPT).Path
} else {
  Write-Host "Downloading Task Studio installer…"
  Invoke-WebRequest -Uri "$base/install.ps1" -OutFile $dest -UseBasicParsing
  if (-not (Test-Path $dest)) {
    throw "Installer download failed."
  }
}

if ($PSVersionTable.PSVersion.Major -ge 6) {
  & $dest @args
} else {
  & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $dest @args
}

if ($LASTEXITCODE -ne 0) {
  throw "Task Studio installer failed with exit code $LASTEXITCODE"
}

if ($PSScriptRoot) {
  exit 0
}
