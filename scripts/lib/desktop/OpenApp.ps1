#Requires -Version 5.1

$tsOpenAppDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $tsOpenAppDir '../health/Health.ps1')

function Test-HttpOk {
  param(
    [string]$Url = $script:AppUiProbeUrl,
    [int]$TimeoutSec = 3
  )
  return (Test-TsUiFingerprint -Url $Url -TimeoutSec $TimeoutSec)
}

function Test-StackEdgeOk {
  param(
    [string]$ComposeFile = 'deploy/docker-compose.yml'
  )
  $pname = if ($env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME } else { 'task-studio' }
  if (Test-Path '.env') {
    foreach ($line in (Get-Content '.env' -ErrorAction SilentlyContinue)) {
      if ($line -match '^COMPOSE_PROJECT_NAME=(.*)$') {
        $pname = $Matches[1].Trim().Trim('"').Trim("'")
        if (-not $pname) { $pname = 'task-studio' }
        break
      }
    }
  }
  return (Test-TsStackEdgeOk -ComposeFile $ComposeFile -ProjectName $pname)
}

function Wait-AppReady {
  param(
    [int]$Tries = 60,
    [int]$SleepSeconds = 3
  )
  for ($i = 0; $i -lt $Tries; $i++) {
    if ((Test-HttpOk) -and (Test-StackEdgeOk)) {
      return $true
    }
    Start-Sleep -Seconds $SleepSeconds
  }
  return $false
}

function Open-AppUi {
  param([string]$Url = $script:AppUiUrl)
  try {
    Start-Process $Url | Out-Null
  } catch {
    if (Get-Command Get-TsText -ErrorAction SilentlyContinue) {
      Write-Host (Get-TsText info_open_manual $Url)
    } else {
      Write-Host "Open in browser: $Url"
    }
  }
}

function Invoke-TsOpen {
  $root = Resolve-TsRoot
  if (-not $root) { throw (Get-TsText err_not_installed_ps) }
  Set-Location $root
  if (Get-Command Ensure-TsEnv -ErrorAction SilentlyContinue) {
    Ensure-TsEnv
  } elseif (Get-Command Resolve-TsHttpPort -ErrorAction SilentlyContinue) {
    [void](Resolve-TsHttpPort)
  }
  if (-not ((Test-HttpOk -TimeoutSec 2) -and (Test-StackEdgeOk))) {
    Write-TsWarn (Get-TsText warn_ui_unreachable $script:AppUiUrl)
  }
  Open-AppUi
  Write-TsInfo (Get-TsText info_opened_ui $script:AppUiUrl)
}
