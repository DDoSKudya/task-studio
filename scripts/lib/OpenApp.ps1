#Requires -Version 5.1
# Shared health / browser helpers for install + start (Windows). Dot-source from scripts.

$script:AppUiUrl = if ($env:TASK_STUDIO_UI_URL) { $env:TASK_STUDIO_UI_URL } else { "http://localhost" }
$script:AppUiProbeUrl = if ($env:TASK_STUDIO_UI_PROBE_URL) { $env:TASK_STUDIO_UI_PROBE_URL } else { "http://127.0.0.1" }

function Test-HttpOk {
  param(
    [string]$Url = $script:AppUiProbeUrl,
    [int]$TimeoutSec = 3
  )
  try {
    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
    return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400)
  } catch {
    return $false
  }
}

function Test-StackEdgeOk {
  param(
    [string]$ComposeFile = "deploy/docker-compose.yml"
  )
  if (-not (Test-Path ".env")) { return $true }
  try {
    $lines = docker compose -f $ComposeFile --env-file .env --profile full ps --format "{{.Service}} {{.State}} {{.Health}}" 2>$null
    $nginx = $lines | Where-Object { $_ -match '^nginx\b' } | Select-Object -First 1
    if (-not $nginx) { return $true }
    return ($nginx -match 'running|healthy')
  } catch {
    return $true
  }
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
  if (-not ((Test-HttpOk -TimeoutSec 2) -and (Test-StackEdgeOk))) {
    Write-TsWarn (Get-TsText warn_ui_unreachable $script:AppUiUrl)
  }
  Open-AppUi
  Write-TsInfo (Get-TsText info_opened_ui $script:AppUiUrl)
}
