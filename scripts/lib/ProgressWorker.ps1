#Requires -Version 5.1
# Background worker for Invoke-TsProgress (UI stays in the parent process).
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

$scriptDir = Join-Path $Root "scripts"
. (Join-Path $scriptDir "lib\I18n.ps1")
. (Join-Path $scriptDir "lib\Ui.ps1")
. (Join-Path $scriptDir "lib\OpenApp.ps1")
. (Join-Path $scriptDir "lib\DesktopShortcuts.ps1")
. (Join-Path $scriptDir "lib\Ops.ps1")

$script:TsLogQuiet = $true
$script:TsLogFile = $LogPath
$script:UpdateReexec = $false
$exitCode = 0

try {
  $actionText = [System.IO.File]::ReadAllText($ActionPath)
  $sb = [scriptblock]::Create($actionText)
  & $sb *>&1 | ForEach-Object {
    $line = ("$_").TrimEnd()
    if ($line) {
      Add-Content -LiteralPath $LogPath -Value $line -Encoding utf8 -ErrorAction SilentlyContinue
    }
  }
  if (-not $script:TsProg -or $script:TsProg.Phase -notin @("done", "error")) {
    Complete-TsProgress
  }
} catch {
  $exitCode = 1
  $msg = $_.Exception.Message
  if (-not $msg) { $msg = "Command failed" }
  Add-Content -LiteralPath $LogPath -Value ("x " + $msg) -Encoding utf8 -ErrorAction SilentlyContinue
  Fail-TsProgress $msg
}

$reexec = if ($script:UpdateReexec) { "1" } else { "0" }
@(
  "ExitCode=$exitCode"
  "Reexec=$reexec"
) | Set-Content -LiteralPath $RcPath -Encoding utf8 -Force
exit $exitCode
