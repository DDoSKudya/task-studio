#Requires -Version 5.1
# UI readiness: port pick + fingerprint (not bare GET / on :80).

$script:TsHttpPortCandidates = @(80, 8080, 18080, 8888, 9080, 3000, 8000)

function Get-TsHttpPortFromEnvFile {
  if (-not (Test-Path '.env')) { return '' }
  foreach ($line in (Get-Content '.env' -ErrorAction SilentlyContinue)) {
    if ($line -match '^TASK_STUDIO_HTTP_PORT=(.*)$') {
      return $Matches[1].Trim().Trim('"').Trim("'")
    }
  }
  return ''
}

function Get-TsPreferredHttpPort {
  if ($env:TASK_STUDIO_HTTP_PORT -match '^\d+$') {
    return [int]$env:TASK_STUDIO_HTTP_PORT
  }
  $fromFile = Get-TsHttpPortFromEnvFile
  if ($fromFile -match '^\d+$') {
    return [int]$fromFile
  }
  return 80
}

function Format-TsUiUrl {
  param([int]$Port = 80)
  if ($Port -eq 80) { return 'http://localhost' }
  return "http://localhost:$Port"
}

function Format-TsUiProbeUrl {
  param([int]$Port = 80)
  if ($Port -eq 80) { return 'http://127.0.0.1/api/health' }
  return "http://127.0.0.1:${Port}/api/health"
}

function Test-TsLoopbackPortBusy {
  param([int]$Port)
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect('127.0.0.1', $Port, $null, $null)
    $ok = $iar.AsyncWaitHandle.WaitOne(250, $false)
    if ($ok) {
      try { $client.EndConnect($iar) } catch { }
      $busy = $client.Connected
      $client.Close()
      return $busy
    }
    $client.Close()
    return $false
  } catch {
    return $false
  }
}

function Test-TsUiFingerprint {
  param(
    [string]$Url = $script:AppUiProbeUrl,
    [int]$TimeoutSec = 3
  )
  try {
    $resp = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec $TimeoutSec -UseBasicParsing
    if ($resp.StatusCode -lt 200 -or $resp.StatusCode -ge 400) {
      return $false
    }
    if ($resp.Headers['X-Task-Studio'] -eq '1') {
      return $true
    }
    $body = [string]$resp.Content
    if ($body -match '"status"\s*:\s*"ok"' -or $body -match '"status"\s*:\s*"degraded"') {
      return $true
    }
    return $false
  } catch {
    return $false
  }
}

function Sync-TsUiEndpointVars {
  param([int]$Port)
  $ui = Format-TsUiUrl -Port $Port
  $probe = Format-TsUiProbeUrl -Port $Port
  $env:TASK_STUDIO_HTTP_PORT = [string]$Port
  if (-not $env:TASK_STUDIO_UI_URL) {
    $env:TASK_STUDIO_UI_URL = $ui
  } elseif ($env:TASK_STUDIO_UI_URL -match '^https?://localhost(:\d+)?/?$' -or
            $env:TASK_STUDIO_UI_URL -match '^https?://127\.0\.0\.1(:\d+)?/?$') {
    $env:TASK_STUDIO_UI_URL = $ui
  }
  $env:TASK_STUDIO_UI_PROBE_URL = $probe
  $script:AppUiUrl = $env:TASK_STUDIO_UI_URL
  $script:AppUiProbeUrl = $probe
}

function Resolve-TsHttpPort {
  <#
    Pick a host port where 127.0.0.1 is free (so probes hit Task Studio, not a
    foreign Windows service bound only to loopback).
  #>
  param(
    [switch]$ForceReselect
  )
  $preferred = Get-TsPreferredHttpPort
  $locked = $false
  if (-not $ForceReselect -and $env:TASK_STUDIO_HTTP_PORT_LOCKED -eq '1') {
    $locked = $true
  }
  if (-not $ForceReselect -and (Get-TsHttpPortFromEnvFile) -match '^\d+$') {
    $existing = [int](Get-TsHttpPortFromEnvFile)
    if ($locked -or (Test-TsUiFingerprint -Url (Format-TsUiProbeUrl -Port $existing) -TimeoutSec 2)) {
      Sync-TsUiEndpointVars -Port $existing
      return $existing
    }
    if (-not (Test-TsLoopbackPortBusy -Port $existing)) {
      Sync-TsUiEndpointVars -Port $existing
      return $existing
    }
  }

  $ordered = @($preferred) + $script:TsHttpPortCandidates | Select-Object -Unique
  foreach ($port in $ordered) {
    if ($port -lt 1 -or $port -gt 65535) { continue }
    if (Test-TsUiFingerprint -Url (Format-TsUiProbeUrl -Port $port) -TimeoutSec 2) {
      Sync-TsUiEndpointVars -Port $port
      return $port
    }
    if (Test-TsLoopbackPortBusy -Port $port) {
      continue
    }
    Sync-TsUiEndpointVars -Port $port
    return $port
  }
  throw "No free HTTP port for Task Studio UI (tried: $($ordered -join ', ')). Set TASK_STUDIO_HTTP_PORT."
}

$script:AppUiUrl = if ($env:TASK_STUDIO_UI_URL) { $env:TASK_STUDIO_UI_URL } else { 'http://localhost' }
$script:AppUiProbeUrl = if ($env:TASK_STUDIO_UI_PROBE_URL) {
  $env:TASK_STUDIO_UI_PROBE_URL
} else {
  'http://127.0.0.1/api/health'
}

function Wait-TsHttpOk {
  param(
    [string]$Url = $script:AppUiProbeUrl,
    [int]$Tries = 60,
    [int]$SleepSec = 3
  )
  for ($i = 1; $i -le $Tries; $i++) {
    if (Test-TsUiFingerprint -Url $Url -TimeoutSec 3) {
      return $true
    }
    Start-Sleep -Seconds $SleepSec
  }
  return $false
}

function Test-TsStackEdgeOk {
  param(
    [string]$ComposeFile = 'deploy/docker-compose.yml',
    [string]$ProjectName = $(if ($env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME } else { 'task-studio' })
  )
  if (-not (Test-Path '.env')) { return $true }
  $line = & docker compose -p $ProjectName -f $ComposeFile --env-file .env --profile full ps --format '{{.Service}} {{.State}} {{.Health}}' 2>$null |
    Where-Object { $_ -match '^nginx\b' } |
    Select-Object -First 1
  if (-not $line) { return $true }
  return ($line -match 'running|healthy')
}

function Get-TsUiFailureHint {
  param([string]$Url = $script:AppUiUrl)
  $port = Get-TsPreferredHttpPort
  $busy = Test-TsLoopbackPortBusy -Port $port
  $finger = Test-TsUiFingerprint -Url $script:AppUiProbeUrl -TimeoutSec 2
  if ($busy -and -not $finger) {
    return (Get-TsText err_ui_port_conflict $port $Url)
  }
  return (Get-TsText err_ui $Url)
}
