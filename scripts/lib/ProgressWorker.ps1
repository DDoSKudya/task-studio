#Requires -Version 5.1
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [Parameter(Mandatory = $true)][string]$SyncPath,
  [Parameter(Mandatory = $true)][string]$LogPath,
  [Parameter(Mandatory = $true)][string]$RcPath,
  [Parameter(Mandatory = $true)][string]$ActionPath
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $Root
$env:TS_PROG_SYNC = $SyncPath

# Requires -Version is on studio; worker is always -File from scripts/lib context.
# Use a distinct name so OpenApp.ps1 cannot clobber it (PS is case-insensitive).
$tsWorkerScriptsDir = Join-Path $Root "scripts"
. (Join-Path $tsWorkerScriptsDir "lib\I18n.ps1")
. (Join-Path $tsWorkerScriptsDir "lib\Ui.ps1")
. (Join-Path $tsWorkerScriptsDir "lib\OpenApp.ps1")
. (Join-Path $tsWorkerScriptsDir "lib\DesktopShortcuts.ps1")
. (Join-Path $tsWorkerScriptsDir "lib\Ops.ps1")

$script:TsLogQuiet = $true
$script:TsLogFile = $LogPath
$env:TS_PROGRESS_LOG = $LogPath
$script:TsProgressLogPath = $LogPath
$script:UpdateReexec = $false
$exitCode = 0

try {
  $actionText = [System.IO.File]::ReadAllText($ActionPath)
  $sb = [scriptblock]::Create($actionText)
  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    & $sb > $LogPath 2>&1
  } finally {
    $ErrorActionPreference = $prevEap
  }
  if (-not $script:TsProg -or $script:TsProg.Phase -notin @("done", "error")) {
    Complete-TsProgress
  }
} catch {
  $exitCode = 1
  $msg = $_.Exception.Message
  if (-not $msg) { $msg = "Command failed" }
  if ((Test-Path $LogPath) -and (Get-Command Get-TsProgressLogSummary -ErrorAction SilentlyContinue)) {
    $fromLog = Get-TsProgressLogSummary -Path $LogPath
    if ($fromLog) { $msg = $fromLog }
  } elseif ($msg -match '(?i)^\s*Image\s+\S+\s+(Building|Built|Pulling|Pulled)\s*$') {
    $msg = Get-TsText cmd_failed_short
  }
  Add-Content -LiteralPath $LogPath -Value ("x " + $msg) -Encoding utf8 -ErrorAction SilentlyContinue
  Fail-TsProgress $msg
}

$reexec = if ($script:UpdateReexec) { "1" } else { "0" }
$uninstallExit = if ($script:UninstallExit) { "1" } else { "0" }
@(
  "ExitCode=$exitCode"
  "Reexec=$reexec"
  "UninstallExit=$uninstallExit"
) | Set-Content -LiteralPath $RcPath -Encoding utf8 -Force
exit $exitCode
