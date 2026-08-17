function Test-TsDockerDesktop {
  $info = & docker info --format '{{.OperatingSystem}} {{.Name}}' 2>$null
  if (-not $info) { return $false }
  return ($info -match 'docker desktop')
}

function Test-TsCanUseHostMetrics {
  if ($env:OS -match 'Windows' -or $IsWindows) { return $false }
  if (Test-TsDockerDesktop) { return $false }
  $sec = & docker info --format '{{.SecurityOptions}}' 2>$null
  if ($sec -match 'rootless') { return $false }
  return $true
}

function Get-TsProfilesArgs {
  $mode = if ($env:ORCHESTRATOR_MODE) { $env:ORCHESTRATOR_MODE } else { 'balancing' }
  $args = @('--profile', 'full')
  if ($mode -ne 'power_saving') {
    $args += @('--profile', 'editor')
  }
  if (Test-TsCanUseHostMetrics) {
    $args += @('--profile', 'host-metrics')
  }
  return $args
}

function Get-TsMemoryLimitsFromProfiles {
  param([string]$Root = (Get-Location).Path)
  $path = Join-Path $Root 'deploy/profiles.json'
  if (-not (Test-Path $path)) {
    throw "profiles.json not found: $path"
  }
  return (Get-Content -Raw -Path $path | ConvertFrom-Json)
}
