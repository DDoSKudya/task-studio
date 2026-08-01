#Requires -Version 5.1
# Ops for studio.ps1 — dot-source after Ui.ps1, OpenApp.ps1, DesktopShortcuts.ps1

$script:ComposeFile = "deploy/docker-compose.yml"
$script:RepoHttps = if ($env:TASK_STUDIO_REPO_HTTPS) { $env:TASK_STUDIO_REPO_HTTPS } else { "https://github.com/DDoSKudya/task-studio.git" }
$script:RepoBranch = if ($env:TASK_STUDIO_BRANCH) { $env:TASK_STUDIO_BRANCH } else { "develop" }
$script:InstallDir = if ($env:TASK_STUDIO_DIR) { $env:TASK_STUDIO_DIR } else { Join-Path $HOME "task-studio" }
$script:MinRamGb = if ($env:TASK_STUDIO_MIN_RAM_GB) { [int]$env:TASK_STUDIO_MIN_RAM_GB } else { 8 }
$script:OllamaModel = if ($env:OLLAMA_MODEL) { $env:OLLAMA_MODEL } else { "qwen2.5:3b" }

# Windows PowerShell 5.1 "utf8" = UTF-8 with BOM — breaks docker --env-file and some JSON readers.
function Write-TsUtf8NoBom {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Content
  )
  $enc = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($Path, $Content, $enc)
}

# Run a native CLI under PS 5.1 without turning stderr into terminating errors
# when $ErrorActionPreference is Stop (studio.ps1 default).
function Invoke-TsNative {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(ValueFromRemainingArguments = $true)][object[]]$ArgumentList
  )
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $output = & $FilePath @ArgumentList 2>&1
    $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    return @{
      ExitCode = $code
      Output   = @($output | ForEach-Object { "$_" })
      Text     = (($output | ForEach-Object { "$_" }) -join "`n").Trim()
    }
  } finally {
    $ErrorActionPreference = $prev
  }
}

function Test-TsDockerReady {
  $r = Invoke-TsNative docker info
  return ($r.ExitCode -eq 0)
}

function Start-TsDockerDesktop {
  if ($env:TASK_STUDIO_NO_AUTO_DOCKER -eq "1") { return $false }

  $running = @(Get-Process -Name "Docker Desktop","com.docker.backend" -ErrorAction SilentlyContinue)
  if ($running.Count -eq 0) {
    $candidates = @(
      (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
      (Join-Path ${env:ProgramFiles(x86)} "Docker\Docker\Docker Desktop.exe")
    )
    $started = $false
    foreach ($exe in $candidates) {
      if ($exe -and (Test-Path -LiteralPath $exe)) {
        try {
          Start-Process -FilePath $exe | Out-Null
          $started = $true
          break
        } catch { }
      }
    }
    if (-not $started) {
      # Last resort: protocol / app user model id varies by install — ignore failures.
      try { Start-Process "Docker Desktop" -ErrorAction SilentlyContinue | Out-Null; $started = $true } catch { }
    }
    return $started
  }
  return $true
}

function Wait-TsDockerReady {
  param([int]$TimeoutSec = 120)
  if ($env:TASK_STUDIO_DOCKER_WAIT_SEC -match '^\d+$') {
    $TimeoutSec = [int]$env:TASK_STUDIO_DOCKER_WAIT_SEC
  }
  if ($TimeoutSec -lt 15) { $TimeoutSec = 15 }
  $elapsed = 0
  while ($elapsed -lt $TimeoutSec) {
    if (Test-TsDockerReady) { return $true }
    if (($elapsed % 10) -eq 0) {
      $msg = Get-TsText status_docker_waiting $elapsed $TimeoutSec
      if ($script:TsProg) {
        $script:TsProg.Status = $msg
        if (Get-Command Write-TsProgSync -ErrorAction SilentlyContinue) { Write-TsProgSync }
      } else {
        Write-TsInfo $msg
      }
    }
    Start-Sleep -Seconds 2
    $elapsed += 2
  }
  return $false
}

function Assert-TsDocker {
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw (Get-TsText err_docker_missing)
  }

  if (-not (Test-TsDockerReady)) {
    $msg = Get-TsText status_docker_starting
    if ($script:TsProg) {
      $script:TsProg.Status = $msg
      if (Get-Command Write-TsProgSync -ErrorAction SilentlyContinue) { Write-TsProgSync }
    } else {
      Write-TsInfo $msg
    }
    [void](Start-TsDockerDesktop)
    if (-not (Wait-TsDockerReady)) {
      $info = Invoke-TsNative docker info
      $detail = $info.Text
      if ($detail -match '(?i)dockerDesktopLinuxEngine|pipe|cannot find the file|daemon is not running|Is the docker daemon running') {
        throw (Get-TsText err_docker_desktop_engine)
      }
      if ($detail) {
        throw (Get-TsText err_docker_unusable $detail)
      }
      throw (Get-TsText err_docker_start_failed)
    }
  }

  $compose = Invoke-TsNative docker compose version
  if ($compose.ExitCode -ne 0) {
    throw (Get-TsText err_compose_missing)
  }
  $env:DOCKER_BUILDKIT = "1"
  $env:COMPOSE_DOCKER_CLI_BUILD = "1"
  $verInfo = Invoke-TsNative docker version --format '{{.Server.Version}}'
  $ver = ($verInfo.Output | Select-Object -First 1)
  if ($ver -match '^(\d+)\.') {
    $major = [int]$Matches[1]
    if ($major -lt 20) {
      throw (Get-TsText err_buildkit $ver)
    }
  }
}

function Get-TsDefaultParallelLimit {
  $ram = Get-TsRamGb
  if ($ram -gt 0 -and $ram -le 8) { return "1" }
  if ($ram -gt 0 -and $ram -le 12) { return "2" }
  if ($ram -gt 0 -and $ram -le 16) { return "3" }
  return "4"
}

function Write-TsInstallPathWarning {
  param([string]$Root = (Get-Location).Path)
  if (-not $Root) { return }
  # Docker Desktop bind-mounts from NTFS (C:\) often break Postgres/ClickHouse permissions.
  if ($Root -match '^[A-Za-z]:\\') {
    Write-TsWarn (Get-TsText warn_path_windows $Root)
  }
}

function Get-TsRamGb {
  try {
    $cs = Get-CimInstance Win32_ComputerSystem
    return [int][math]::Floor($cs.TotalPhysicalMemory / 1GB)
  } catch {
    return 0
  }
}

function Resolve-TsRoot {
  if ((Test-Path $script:ComposeFile) -and (Test-Path ".env")) {
    return (Get-Location).Path
  }
  if (Test-Path $script:ComposeFile) {
    return (Get-Location).Path
  }
  $homeRepo = $script:InstallDir
  if (Test-Path (Join-Path $homeRepo $script:ComposeFile)) {
    Set-Location $homeRepo
    return (Get-Location).Path
  }
  return $null
}

function Ensure-TsRepo {
  if ((Test-Path $script:ComposeFile) -and (Test-Path ".env.example")) {
    return (Get-Location).Path
  }
  $candidate = Join-Path $script:InstallDir $script:ComposeFile
  if (Test-Path $candidate) {
    Set-Location $script:InstallDir
    return (Get-Location).Path
  }
  Write-TsInfo (Get-TsText info_clone $script:InstallDir)
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw (Get-TsText err_git) }
  $parent = Split-Path -Parent $script:InstallDir
  if ($parent -and -not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
  git clone --branch $script:RepoBranch --depth 1 $script:RepoHttps $script:InstallDir
  Set-Location $script:InstallDir
  return (Get-Location).Path
}

function Get-TsEnvValue([string]$Name) {
  $envPath = Join-Path (Get-Location).Path ".env"
  if (-not (Test-Path $envPath)) { return "" }
  $raw = [System.IO.File]::ReadAllText($envPath)
  if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 0xFEFF) {
    $raw = $raw.Substring(1)
  }
  foreach ($line in ($raw -split "`r?`n")) {
    if ($line -match "^$Name=(.*)$") {
      return $Matches[1].Trim().Trim('"').Trim("'")
    }
  }
  return ""
}

function Set-TsEnvValue([string]$Name, [string]$Value) {
  $envPath = Join-Path (Get-Location).Path ".env"
  $raw = if (Test-Path $envPath) {
    [System.IO.File]::ReadAllText($envPath)
  } else {
    ""
  }
  if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 0xFEFF) {
    $raw = $raw.Substring(1)
  }
  $lines = New-Object System.Collections.Generic.List[string]
  foreach ($line in ($raw -split "`r?`n", -1)) {
    # Drop trailing empty split artifact only if file ended with newline — keep content lines.
    [void]$lines.Add($line)
  }
  if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -eq "") {
    $lines.RemoveAt($lines.Count - 1)
  }
  $found = $false
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match "^$Name=") {
      $lines[$i] = "$Name=$Value"
      $found = $true
      break
    }
  }
  if (-not $found) { [void]$lines.Add("$Name=$Value") }
  Write-TsUtf8NoBom -Path $envPath -Content (($lines -join "`n") + "`n")
}

function New-TsMasterKey {
  $bytes = New-Object byte[] 32
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  return [Convert]::ToBase64String($bytes)
}

function New-TsJwtSecret {
  $bytes = New-Object byte[] 48
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  return [Convert]::ToBase64String($bytes)
}

function Test-TsMasterKey([string]$Raw) {
  if (-not $Raw -or $Raw.ToLower().Contains("change-me")) { return $false }
  try {
    $decoded = [Convert]::FromBase64String($Raw)
    return $decoded.Length -eq 32
  } catch {
    return $false
  }
}

function Get-TsDockerSockGid {
  # Docker Desktop / Linux VM: read GID of the mounted socket so orchestrator group_add works.
  try {
    $r = Invoke-TsNative docker run --rm -v /var/run/docker.sock:/var/run/docker.sock alpine:3.20 `
      stat -c '%g' /var/run/docker.sock
    if ($r.ExitCode -ne 0) { return "" }
    $gid = ($r.Text).Trim()
    if ($gid -match '^\d+$') { return $gid }
  } catch { }
  return ""
}

function Ensure-TsEnv {
  if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-TsInfo (Get-TsText info_env_created)
  }
  # Normalize possible UTF-8 BOM from editors / older launcher builds.
  $envPath = Join-Path (Get-Location).Path ".env"
  $raw = [System.IO.File]::ReadAllText($envPath)
  if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 0xFEFF) {
    Write-TsUtf8NoBom -Path $envPath -Content $raw.Substring(1)
  }
  $key = Get-TsEnvValue "SECRETS_MASTER_KEY"
  if (-not (Test-TsMasterKey $key)) {
    Set-TsEnvValue "SECRETS_MASTER_KEY" (New-TsMasterKey)
    Write-TsInfo (Get-TsText info_secrets_key)
  }
  $jwt = Get-TsEnvValue "JWT_SECRET"
  if (-not $jwt -or $jwt.ToLower().Contains("change-me") -or $jwt.Length -lt 16) {
    Set-TsEnvValue "JWT_SECRET" (New-TsJwtSecret)
    Write-TsInfo (Get-TsText info_jwt)
  }
  $model = Get-TsEnvValue "OLLAMA_MODEL"
  if (-not $model -or $model -eq "llama3.2") {
    Set-TsEnvValue "OLLAMA_MODEL" $script:OllamaModel
  }
  $packMax = Get-TsEnvValue "PACK_MAX_UPLOAD_MB"
  if (-not $packMax) {
    Set-TsEnvValue "PACK_MAX_UPLOAD_MB" "500"
  }
  # Only probe the socket when GID is missing or still the .env.example placeholder.
  $curGid = Get-TsEnvValue "DOCKER_GID"
  if (-not $curGid -or $curGid -eq "988") {
    $gid = Get-TsDockerSockGid
    if ($gid) {
      Set-TsEnvValue "DOCKER_GID" $gid
    }
  }
}

function Initialize-TsComposeEnv {
  $pname = Get-TsEnvValue "COMPOSE_PROJECT_NAME"
  if (-not $pname) { $pname = "task-studio" }
  $env:COMPOSE_PROJECT_NAME = $pname
  if (-not $env:COMPOSE_PARALLEL_LIMIT) {
    $env:COMPOSE_PARALLEL_LIMIT = (Get-TsDefaultParallelLimit)
  }
  $env:DOCKER_BUILDKIT = "1"
  $env:COMPOSE_DOCKER_CLI_BUILD = "1"
  return $pname
}

function Invoke-TsCompose {
  param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]]$ComposeArgs
  )
  $pname = Initialize-TsComposeEnv
  $argList = @("compose", "-p", $pname, "-f", $script:ComposeFile)
  if (Test-Path ".env") {
    $argList += @("--env-file", ".env")
  }
  if ($ComposeArgs) { $argList += $ComposeArgs }
  # Docker prints progress on stderr; under Stop that becomes NativeCommandError.
  $r = Invoke-TsNative docker @argList
  foreach ($line in $r.Output) {
    Write-Output $line
  }
  $global:LASTEXITCODE = $r.ExitCode
  return $r.ExitCode
}

function Invoke-TsComposeCaptured {
  param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]]$ComposeArgs
  )
  $pname = Initialize-TsComposeEnv
  $argList = @("compose", "-p", $pname, "-f", $script:ComposeFile)
  if (Test-Path ".env") {
    $argList += @("--env-file", ".env")
  }
  if ($ComposeArgs) { $argList += $ComposeArgs }
  $r = Invoke-TsNative docker @argList
  $global:LASTEXITCODE = $r.ExitCode
  return ,$r.Output
}

function Prepare-TsDirs {
  @(
    "data/postgres", "data/redis", "data/rabbitmq", "data/packs",
    "data/meilisearch", "data/clickhouse", "data/minio", "data/ollama",
    "data/grafana", "data/prometheus", "data/piston/packages",
    "data/logs"
  ) | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
}

function Write-TsComposeFailureDiagnostics {
  $log = $null
  if ($script:TsLogFile) {
    $log = [string]$script:TsLogFile
  } elseif ($script:TsProgressLogPath) {
    $log = [string]$script:TsProgressLogPath
  } elseif ($env:TS_PROGRESS_LOG) {
    $log = $env:TS_PROGRESS_LOG
  } elseif (Test-Path "data/logs") {
    $log = (Join-Path (Get-Location).Path "data/logs/studio-last.log")
  }
  if (-not $log) { return }
  try {
    $pname = if ($env:COMPOSE_PROJECT_NAME) { $env:COMPOSE_PROJECT_NAME } else { "task-studio" }
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("===== compose failure diagnostics =====")
    [void]$sb.AppendLine(("project={0} time={1:u}" -f $pname, (Get-Date).ToUniversalTime()))
    try {
      $psOut = @(Invoke-TsComposeCaptured @("ps", "-a"))
      foreach ($line in $psOut) { [void]$sb.AppendLine([string]$line) }
    } catch {
      [void]$sb.AppendLine(("compose ps failed: {0}" -f $_.Exception.Message))
    }
    $priority = @("catalog", "auth", "postgres", "grading", "media")
    $names = New-Object System.Collections.Generic.List[string]
    foreach ($svc in $priority) {
      $n = "task-studio-${svc}-1"
      [void]$names.Add($n)
    }
    $rowsR = Invoke-TsNative docker ps -a --filter "label=com.docker.compose.project=$pname" --format "{{.Names}}`t{{.Status}}"
    $rows = @($rowsR.Output)
    foreach ($row in $rows) {
      if (-not $row) { continue }
      $parts = ([string]$row) -split "`t", 2
      $name = $parts[0]
      $status = if ($parts.Count -gt 1) { $parts[1] } else { "" }
      if ($status -notmatch '(?i)unhealthy|Exited|Dead|Restarting') { continue }
      if (-not $names.Contains($name)) { [void]$names.Add($name) }
    }
    foreach ($name in $names) {
      $insp = Invoke-TsNative docker inspect $name
      if ($insp.ExitCode -ne 0) { continue }
      $statusR = Invoke-TsNative docker inspect --format "{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{end}}" $name
      $status = [string]$statusR.Text
      [void]$sb.AppendLine("")
      [void]$sb.AppendLine(("----- logs: {0} ({1}) -----" -f $name, $status))
      $logsR = Invoke-TsNative docker logs --tail 200 $name
      foreach ($line in $logsR.Output) { [void]$sb.AppendLine([string]$line) }
      if ($logsR.ExitCode -ne 0 -and $logsR.Output.Count -eq 0) {
        [void]$sb.AppendLine(("docker logs failed: exit {0}" -f $logsR.ExitCode))
      }
    }
    $payload = $sb.ToString()
    # Prefer .NET append — works while the worker still has the file open for redirect.
    try {
      [System.IO.File]::AppendAllText($log, $payload, (New-Object System.Text.UTF8Encoding $false))
    } catch {
      Add-Content -LiteralPath $log -Value $payload -Encoding utf8 -ErrorAction SilentlyContinue
    }
  } catch { }
}

function Wait-TsCatalogHealthy {
  param([int]$TimeoutSec = 240)
  $name = "task-studio-catalog-1"
  $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
  $sawRunning = $false
  while ([DateTime]::UtcNow -lt $deadline) {
    $insp = Invoke-TsNative docker inspect $name
    if ($insp.ExitCode -eq 0) {
      $healthR = Invoke-TsNative docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{end}}" $name
      $statusR = Invoke-TsNative docker inspect --format "{{.State.Status}}" $name
      $health = [string]$healthR.Text
      $status = [string]$statusR.Text
      if ($status -eq "running") { $sawRunning = $true }
      if ($health -eq "healthy") { return $true }
      if ($health -eq "unhealthy") {
        Write-TsComposeFailureDiagnostics
        return $false
      }
      if ($status -eq "exited" -or $status -eq "dead") {
        Write-TsComposeFailureDiagnostics
        return $false
      }
      if ($script:TsProg -and $sawRunning) {
        $left = [int][Math]::Max(0, ($deadline - [DateTime]::UtcNow).TotalSeconds)
        $script:TsProg.Status = (Get-TsText status_waiting_catalog $left)
        if (Get-Command Write-TsProgSync -ErrorAction SilentlyContinue) { Write-TsProgSync }
      }
    }
    Start-Sleep -Seconds 3
  }
  Write-TsComposeFailureDiagnostics
  return $false
}

function Invoke-TsComposeUp {
  param([object[]]$ProfileArgs)
  $msg = Get-TsText status_starting_infra
  if ($script:TsProg) {
    $script:TsProg.Status = $msg
    if (Get-Command Write-TsProgSync -ErrorAction SilentlyContinue) { Write-TsProgSync }
  } else {
    Write-TsInfo $msg
  }
  [void](Invoke-TsCompose @($ProfileArgs + @("up", "-d", "postgres", "redis", "rabbitmq", "minio", "meilisearch")))
  Invoke-TsCompose @($ProfileArgs + @("up", "-d", "--wait", "--wait-timeout", "180", "postgres", "redis", "rabbitmq"))
  if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    Write-TsComposeFailureDiagnostics
    return $false
  }

  $catMsg = Get-TsText status_starting_catalog
  if ($script:TsProg) {
    $script:TsProg.Status = $catMsg
    if (Get-Command Write-TsProgSync -ErrorAction SilentlyContinue) { Write-TsProgSync }
  }
  Invoke-TsCompose @($ProfileArgs + @("up", "-d", "--no-deps", "catalog"))
  $catalogOk = Wait-TsCatalogHealthy -TimeoutSec 240
  if (-not $catalogOk) {
    [void](Invoke-TsCompose @($ProfileArgs + @("up", "-d", "--force-recreate", "--no-deps", "catalog")))
    $catalogOk = Wait-TsCatalogHealthy -TimeoutSec 240
  }
  if (-not $catalogOk) {
    # Soft-gate: UI (nginx/web/studio-api) does not require catalog healthy.
    Write-TsWarn (Get-TsText warn_catalog_continue)
    Write-TsComposeFailureDiagnostics
  }

  $startMsg = Get-TsText status_starting_containers
  if ($script:TsProg) {
    $script:TsProg.Status = $startMsg
    if (Get-Command Write-TsProgSync -ErrorAction SilentlyContinue) { Write-TsProgSync }
  }
  Invoke-TsCompose @($ProfileArgs + @("up", "-d", "--remove-orphans"))
  if (-not $LASTEXITCODE -or $LASTEXITCODE -eq 0) { return $true }
  Start-Sleep -Seconds 10
  Invoke-TsCompose @($ProfileArgs + @("up", "-d", "--remove-orphans"))
  if (-not $LASTEXITCODE -or $LASTEXITCODE -eq 0) { return $true }
  Write-TsComposeFailureDiagnostics
  return $false
}

function Get-TsProfileArgs {
  # Prefer process env (install may force power_saving on low RAM). Fall back to .env.
  $mode = "balancing"
  if ($env:ORCHESTRATOR_MODE) {
    $mode = $env:ORCHESTRATOR_MODE
  } elseif (Test-Path ".env") {
    $line = Get-Content ".env" | Where-Object { $_ -match '^ORCHESTRATOR_MODE=' } | Select-Object -First 1
    if ($line) {
      $mode = ($line -split '=', 2)[1].Trim()
      $env:ORCHESTRATOR_MODE = $mode
    }
  }
  $args = @("--profile", "full")
  if ($mode -ne "power_saving") { $args += @("--profile", "editor") }
  return ,$args
}

function Invoke-TsInstall {
  Assert-TsDocker
  $plan = @(
    @{ Id = "prepare"; Label = (Get-TsText stage_prepare); Est = 40 }
    @{ Id = "build"; Label = (Get-TsText stage_build); Est = 600 }
    @{ Id = "start"; Label = (Get-TsText stage_start); Est = 50 }
    @{ Id = "health"; Label = (Get-TsText stage_health); Est = 90 }
    @{ Id = "model"; Label = (Get-TsText stage_model); Est = 240 }
    @{ Id = "finish"; Label = (Get-TsText stage_finish); Est = 25 }
  )

  Enter-TsProgressStage -Plan $plan -Id "prepare" -Status (Get-TsText status_check_docker)
  $ram = Get-TsRamGb
  if ($ram -gt 0 -and $ram -lt $script:MinRamGb) {
    throw (Get-TsText err_ram $ram $script:MinRamGb)
  }
  if ($ram -gt 0 -and $ram -lt 16) {
    $env:ORCHESTRATOR_MODE = if ($env:ORCHESTRATOR_MODE) { $env:ORCHESTRATOR_MODE } else { "power_saving" }
    Enter-TsProgressStage -Plan $plan -Id "prepare" -Status (Get-TsText status_ram_power $ram)
  }

  $root = Ensure-TsRepo
  Set-Location $root
  Write-TsInstallPathWarning -Root $root
  Ensure-TsEnv
  if ($ram -gt 0 -and $ram -lt 16) {
    Set-TsEnvValue "ORCHESTRATOR_MODE" $env:ORCHESTRATOR_MODE
  }
  Prepare-TsDirs
  $profileArgs = Get-TsProfileArgs
  Enter-TsProgressStage -Plan $plan -Id "prepare" -Status (Get-TsText status_build_parallel (Get-TsDefaultParallelLimit))

  Enter-TsProgressStage -Plan $plan -Id "build" -Status (Get-TsText status_build_slow)
  Invoke-TsCompose @($profileArgs + @("build"))
  if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw (Get-TsText err_build_short) }

  Enter-TsProgressStage -Plan $plan -Id "start" -Status (Get-TsText status_starting_containers)
  if (-not (Invoke-TsComposeUp -ProfileArgs $profileArgs)) {
    throw (Get-TsText err_up_short)
  }

  Enter-TsProgressStage -Plan $plan -Id "health" -Status (Get-TsText status_waiting_ui $script:AppUiUrl)
  if (Wait-AppReady -Tries 90 -SleepSeconds 5) {
    Enter-TsProgressStage -Plan $plan -Id "health" -Status (Get-TsText status_ui_ok)
  } else {
    throw (Get-TsText err_ui $script:AppUiUrl)
  }

  Enter-TsProgressStage -Plan $plan -Id "model" -Status (Get-TsText status_pull_model)
  $modelLine = (Get-Content .env | Where-Object { $_ -match '^OLLAMA_MODEL=' } | Select-Object -First 1)
  $model = if ($modelLine) { ($modelLine -split '=', 2)[1].Trim() } else { $script:OllamaModel }
  try {
    Invoke-TsCompose @("--profile", "full", "exec", "-T", "ollama", "ollama", "pull", $model)
  } catch {
    Write-TsWarn (Get-TsText warn_model_pull_short)
  }

  Enter-TsProgressStage -Plan $plan -Id "finish" -Status (Get-TsText status_creating_shortcuts)
  try {
    Install-TaskStudioDesktopShortcuts -Root $root
  } catch {
    Write-TsWarn (Get-TsText warn_shortcuts $_.Exception.Message)
  }

  Complete-TsProgress
  Write-Host (Get-TsText info_dir $root)
  Write-Host (Get-TsText info_ui $script:AppUiUrl)
  Write-Host (Get-TsText info_console_ps)
}

function Invoke-TsStart {
  $plan = @(
    @{ Id = "prepare"; Label = (Get-TsText stage_prepare); Est = 20 }
    @{ Id = "start"; Label = (Get-TsText stage_start); Est = 40 }
    @{ Id = "health"; Label = (Get-TsText stage_health); Est = 60 }
  )
  Enter-TsProgressStage -Plan $plan -Id "prepare" -Status (Get-TsText status_locate)
  Assert-TsDocker
  $root = Resolve-TsRoot
  if (-not $root) { throw (Get-TsText err_not_installed_ps) }
  Set-Location $root
  Ensure-TsEnv
  $profileArgs = Get-TsProfileArgs

  Enter-TsProgressStage -Plan $plan -Id "start" -Status (Get-TsText status_starting_ts)
  if (-not (Invoke-TsComposeUp -ProfileArgs $profileArgs)) {
    throw (Get-TsText err_up_short)
  }

  Enter-TsProgressStage -Plan $plan -Id "health" -Status (Get-TsText status_check_ui $script:AppUiProbeUrl)
  if (Wait-AppReady -Tries 60 -SleepSeconds 3) {
    Enter-TsProgressStage -Plan $plan -Id "health" -Status (Get-TsText status_ui_ok)
    Complete-TsProgress
  } else {
    throw (Get-TsText err_ui $script:AppUiUrl)
  }
}

function Get-TsRunningCount {
  if (-not (Test-Path $script:ComposeFile) -or -not (Test-Path ".env")) { return 0 }
  if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { return 0 }
  try {
    $lines = Invoke-TsComposeCaptured @(
      "--profile", "full", "--profile", "editor", "--profile", "host-metrics",
      "ps", "--format", "{{.State}}"
    )
    if (-not $lines) { return 0 }
    return @($lines | ForEach-Object { "$_" } | Where-Object { $_ -match '(?i)running|healthy' }).Count
  } catch {
    return 0
  }
}

# missing | stopped | running
function Get-TsStackState {
  $root = Resolve-TsRoot
  if (-not $root) {
    if (Test-Path $script:ComposeFile) {
      if (-not (Test-Path ".env")) { return "missing" }
    } else {
      return "missing"
    }
  } else {
    Set-Location $root
  }
  if (-not (Test-Path ".env")) { return "missing" }
  if ((Get-TsRunningCount) -gt 0) { return "running" }
  return "stopped"
}

function Ensure-TsStopped {
  $profiles = @("--profile", "full", "--profile", "editor", "--profile", "host-metrics")
  $logPath = $null
  if ($script:TsProg -and $script:TsProg.LogPath) { $logPath = $script:TsProg.LogPath }
  try {
    $downOut = @()
    if (Test-Path ".env") {
      $downOut = @(Invoke-TsComposeCaptured @($profiles + @("down", "--remove-orphans")))
    } elseif (Test-Path $script:ComposeFile) {
      $pname = Initialize-TsComposeEnv
      $downOut = @(docker compose -p $pname -f $script:ComposeFile @profiles down --remove-orphans 2>&1)
    }
    if ($logPath -and $downOut) {
      Add-Content -Path $logPath -Value (($downOut | ForEach-Object { "$_" }) -join "`n") -Encoding utf8 -ErrorAction SilentlyContinue
    }
    # Legacy installs used project name from compose path (`deploy`).
    $legacy = @(docker compose -p deploy -f $script:ComposeFile ps -q 2>$null)
    if ($legacy) {
      $legacyOut = @(docker compose -p deploy -f $script:ComposeFile @profiles down --remove-orphans 2>&1)
      if ($logPath -and $legacyOut) {
        Add-Content -Path $logPath -Value (($legacyOut | ForEach-Object { "$_" }) -join "`n") -Encoding utf8 -ErrorAction SilentlyContinue
      }
    }
  } catch {
    if ($logPath) {
      Add-Content -Path $logPath -Value $_.Exception.Message -Encoding utf8 -ErrorAction SilentlyContinue
    }
  }
  for ($i = 0; $i -lt 30; $i++) {
    if ((Get-TsRunningCount) -eq 0) { return $true }
    Start-Sleep -Seconds 1
  }
  return ((Get-TsRunningCount) -eq 0)
}

function Invoke-TsStop {
  $plan = @(
    @{ Id = "prepare"; Label = (Get-TsText stage_prepare); Est = 10 }
    @{ Id = "stop"; Label = (Get-TsText stage_stop); Est = 30 }
  )
  Enter-TsProgressStage -Plan $plan -Id "prepare" -Status (Get-TsText status_locate_short)
  $root = Resolve-TsRoot
  if (-not $root) { throw (Get-TsText err_compose_missing_file $script:ComposeFile) }
  Set-Location $root
  if (-not (Test-Path ".env")) { throw (Get-TsText err_no_env_stop) }

  Enter-TsProgressStage -Plan $plan -Id "stop" -Status (Get-TsText status_stopping)
  if (-not (Ensure-TsStopped)) {
    throw (Get-TsText err_still_running)
  }
  Complete-TsProgress
}

function Invoke-TsRestart {
  $plan = @(
    @{ Id = "stop"; Label = (Get-TsText stage_stop); Est = 35 }
    @{ Id = "start"; Label = (Get-TsText stage_start); Est = 40 }
    @{ Id = "health"; Label = (Get-TsText stage_health); Est = 60 }
  )
  Enter-TsProgressStage -Plan $plan -Id "stop" -Status (Get-TsText status_stopping)
  Assert-TsDocker
  $root = Resolve-TsRoot
  if (-not $root) { throw (Get-TsText err_not_installed_ps) }
  Set-Location $root
  if (-not (Test-Path ".env")) { throw (Get-TsText err_no_env_install) }
  Ensure-TsEnv
  if (-not (Ensure-TsStopped)) { throw (Get-TsText err_stop_before_restart) }

  $profileArgs = Get-TsProfileArgs
  Enter-TsProgressStage -Plan $plan -Id "start" -Status (Get-TsText status_starting_containers)
  if (-not (Invoke-TsComposeUp -ProfileArgs $profileArgs)) {
    throw (Get-TsText err_up_after_restart)
  }

  Enter-TsProgressStage -Plan $plan -Id "health" -Status (Get-TsText status_check_ui $script:AppUiProbeUrl)
  if (Wait-AppReady -Tries 60 -SleepSeconds 3) {
    Enter-TsProgressStage -Plan $plan -Id "health" -Status (Get-TsText status_ui_ok)
    Complete-TsProgress
  } else {
    throw (Get-TsText err_ui_after_restart $script:AppUiUrl)
  }
}

function Test-TsConsumerRoot {
  param([string]$Root = (Get-Location).Path)
  if (Test-Path (Join-Path $Root ".studio-consumer")) { return $true }
  $want = $null
  if (Test-Path $script:InstallDir) { $want = (Resolve-Path $script:InstallDir).Path }
  return ($want -and ($Root -eq $want))
}

function Test-TsSafePurgeRoot {
  param([string]$Root)
  if (-not $Root) { return $false }
  try { $Root = (Resolve-Path $Root).Path } catch { return $false }
  if ($Root -eq '\' -or $Root -match '^[A-Za-z]:\\?$') { return $false }
  if ($Root -eq $HOME -or $Root -eq $env:USERPROFILE) { return $false }
  return (Test-TsConsumerRoot -Root $Root)
}

function Start-TsDeferredDeleteRoot {
  param([string]$Root)
  $Root = (Resolve-Path $Root).Path
  $parent = Split-Path -Parent $Root
  Set-Location $parent
  $escaped = $Root.Replace("'", "''")
  $cmd = @"
Start-Sleep -Seconds 2
`$target = '$escaped'
for (`$i = 0; `$i -lt 20; `$i++) {
  try {
    if (-not (Test-Path -LiteralPath `$target)) { exit 0 }
    Remove-Item -LiteralPath `$target -Recurse -Force -ErrorAction Stop
    exit 0
  } catch {
    Start-Sleep -Seconds 1
  }
}
exit 1
"@
  Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList @(
    "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $cmd
  ) | Out-Null
  $script:UninstallExit = $true
  # Parent progress UI runs work in a child process — sticky marker for menu exit.
  try {
    Set-Content -LiteralPath (Join-Path $Root ".studio-uninstall-exit") -Value "1" -Encoding ascii -Force
  } catch { }
  if ($script:TsProg) {
    $script:TsProg.Status = (Get-TsText status_delete_scheduled $Root)
    Write-TsProgSync
  } else {
    Write-TsInfo (Get-TsText status_delete_scheduled $Root)
  }
}

# Returns $null on cancel, otherwise @{ Purge = $bool }.
function Confirm-TsUninstallConsent {
  param([switch]$Yes, [switch]$Purge)
  if ($env:TASK_STUDIO_UNINSTALL_YES -eq "1") { $Yes = $true }

  $root = Resolve-TsRoot
  if (-not $root) { throw (Get-TsText err_install_not_found) }
  Set-Location $root
  Remove-Item -LiteralPath (Join-Path $root ".studio-uninstall-exit") -Force -ErrorAction SilentlyContinue

  if (Test-TsConsumerRoot -Root $root) { $Purge = $true }

  if (-not $Yes) {
    Write-TsWarn (Get-TsText warn_uninstall)
    if ($Purge) {
      if (Test-TsConsumerRoot -Root $root) {
        Write-TsWarn (Get-TsText warn_purge_launcher $root)
      } else {
        Write-TsWarn (Get-TsText warn_purge_ps $root)
      }
      if (-not (Confirm-TsDelete (Get-TsText confirm_uninstall))) {
        Write-TsInfo (Get-TsText info_cancelled)
        return $null
      }
    } else {
      if (-not (Confirm-TsDelete (Get-TsText confirm_uninstall))) {
        Write-TsInfo (Get-TsText info_cancelled)
        return $null
      }
      if (Confirm-Ts (Get-TsText confirm_purge)) {
        $Purge = $true
        Write-TsWarn (Get-TsText warn_purge_ps $root)
      }
    }
  }

  return @{ Purge = [bool]$Purge }
}

function Test-TsUninstallShouldExit {
  param([string]$Root = (Get-Location).Path)
  $marker = Join-Path $Root ".studio-uninstall-exit"
  if (Test-Path -LiteralPath $marker) {
    Remove-Item -LiteralPath $marker -Force -ErrorAction SilentlyContinue
    $script:UninstallExit = $true
    return $true
  }
  return [bool]$script:UninstallExit
}

function Invoke-TsUninstall {
  param([switch]$Yes, [switch]$Purge)
  $script:UninstallExit = $false
  if ($env:TASK_STUDIO_UNINSTALL_YES -eq "1") { $Yes = $true }
  if ($env:TASK_STUDIO_UNINSTALL_PURGE -eq "1") { $Purge = $true }

  if (-not $Yes) {
    $consent = Confirm-TsUninstallConsent -Yes:$Yes -Purge:$Purge
    if (-not $consent) { return }
    $Purge = $consent.Purge
  }

  $root = Resolve-TsRoot
  if (-not $root) { throw (Get-TsText err_install_not_found) }
  Set-Location $root
  if (Test-TsConsumerRoot -Root $root) { $Purge = $true }

  $plan = @(
    @{ Id = "stop"; Label = (Get-TsText stage_stop); Est = 30 }
    @{ Id = "remove"; Label = (Get-TsText stage_remove); Est = 40 }
    @{ Id = "files"; Label = (Get-TsText stage_files); Est = 20 }
    @{ Id = "finish"; Label = (Get-TsText stage_finish); Est = 10 }
  )
  Assert-TsDocker
  Enter-TsProgressStage -Plan $plan -Id "stop" -Status (Get-TsText status_ensure_stopped)
  if (-not (Ensure-TsStopped)) {
    throw (Get-TsText err_uninstall_running)
  }

  Enter-TsProgressStage -Plan $plan -Id "remove" -Status (Get-TsText status_remove_vol)
  $profiles = @("--profile", "full", "--profile", "editor", "--profile", "host-metrics")
  try {
    if (Test-Path ".env") {
      Invoke-TsCompose @($profiles + @("down", "-v", "--rmi", "local", "--remove-orphans"))
    } else {
      $pname = Initialize-TsComposeEnv
      docker compose -p $pname -f $script:ComposeFile @profiles down -v --rmi local --remove-orphans
    }
    $legacy = @(docker compose -p deploy -f $script:ComposeFile ps -q 2>$null)
    if ($legacy) {
      docker compose -p deploy -f $script:ComposeFile @profiles down -v --rmi local --remove-orphans
    }
  } catch {
    Write-TsWarn (Get-TsText warn_compose_down $_.Exception.Message)
  }

  Enter-TsProgressStage -Plan $plan -Id "files" -Status (Get-TsText status_remove_files)
  try { Remove-TaskStudioDesktopShortcuts } catch { Write-TsWarn $_.Exception.Message }

  Enter-TsProgressStage -Plan $plan -Id "finish" -Status (Get-TsText status_cleanup)
  if ($Purge) {
    if (Test-TsSafePurgeRoot -Root $root) {
      Start-TsDeferredDeleteRoot -Root $root
    } else {
      $dataPath = Join-Path $root "data"
      if (Test-Path $dataPath) { Remove-Item -Recurse -Force $dataPath }
      $envPath = Join-Path $root ".env"
      if (Test-Path $envPath) { Remove-Item -Force $envPath }
      Write-TsWarn (Get-TsText warn_purge_skip_got $script:InstallDir $root)
    }
  } else {
    $dataPath = Join-Path $root "data"
    if (Test-Path $dataPath) { Remove-Item -Recurse -Force $dataPath }
    $envPath = Join-Path $root ".env"
    if (Test-Path $envPath) { Remove-Item -Force $envPath }
    Write-TsInfo (Get-TsText status_repo_kept)
  }
  Complete-TsProgress
}

# --- Self-update (HTTP version + archive, no git) ----------------------------

$script:UpdateTtlSec = if ($env:TASK_STUDIO_UPDATE_TTL_SEC) { [int]$env:TASK_STUDIO_UPDATE_TTL_SEC } else { 3600 }
$script:UpdateAvailable = $false
$script:UpdateSummary = ""
$script:UpdateStatus = ""
$script:UpdateReexec = $false
$script:UpdateRemoteVersion = ""
$script:UpdateLocalVersion = ""
$script:UpdateRemoteArchive = ""

function Get-TsUpdateStampPath {
  param([string]$Root = (Get-Location).Path)
  Join-Path $Root ".studio-update-check"
}

function Get-TsUpdateCachePath {
  param([string]$Root = (Get-Location).Path)
  Join-Path $Root ".studio-update-cache.json"
}

function Get-TsUpdateStatePath {
  param([string]$Root = (Get-Location).Path)
  Join-Path $Root ".studio-state.json"
}

function Get-TsVersionManifestUrl {
  if ($env:TASK_STUDIO_VERSION_URL) { return $env:TASK_STUDIO_VERSION_URL }
  $branch = if ($env:TASK_STUDIO_BRANCH) { $env:TASK_STUDIO_BRANCH } else { $script:RepoBranch }
  return "https://raw.githubusercontent.com/DDoSKudya/task-studio/$branch/studio-version.json"
}

function Test-TsUpdateShouldFetch {
  param([switch]$Force)
  if ($Force) { return $true }
  $stamp = Get-TsUpdateStampPath
  if (-not (Test-Path $stamp)) { return $true }
  try {
    $last = [int64]((Get-Content $stamp -Raw).Trim())
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    return (($now - $last) -ge $script:UpdateTtlSec)
  } catch {
    return $true
  }
}

function Set-TsUpdateStamp {
  $stamp = Get-TsUpdateStampPath
  [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() | Set-Content -Path $stamp -Encoding ascii -NoNewline
}

function Get-TsJsonValue {
  param([string]$Path, [string]$Key, [string]$JsonText = $null)
  try {
    $obj = if ($JsonText) { $JsonText | ConvertFrom-Json } else { Get-Content -Raw -Path $Path | ConvertFrom-Json }
    $v = $obj.$Key
    if ($null -eq $v) { return "" }
    return [string]$v
  } catch {
    return ""
  }
}

function Get-TsLocalVersion {
  $state = Get-TsUpdateStatePath
  if (Test-Path $state) {
    $v = Get-TsJsonValue -Path $state -Key version
    if ($v) { return $v }
  }
  if (Test-Path "studio-version.json") {
    $v = Get-TsJsonValue -Path "studio-version.json" -Key version
    if ($v) { return $v }
  }
  return "0"
}

function Write-TsUpdateState {
  param([string]$Version, [string]$ContentSha = "")
  $state = Get-TsUpdateStatePath
  $payload = (@{ version = $Version; content_sha256 = $ContentSha } | ConvertTo-Json) + "`n"
  Write-TsUtf8NoBom -Path $state -Content $payload
}

function Set-TsConsumerMarker {
  param([string]$Root = (Get-Location).Path)
  New-Item -ItemType File -Path (Join-Path $Root ".studio-consumer") -Force | Out-Null
}

function Test-TsUpdatableInstall {
  $root = (Get-Location).Path
  if (Test-Path (Join-Path $root ".studio-consumer")) { return $true }
  if ($env:TASK_STUDIO_ALLOW_SELF_UPDATE -eq "1") { return $true }
  $want = $null
  if (Test-Path $script:InstallDir) {
    $want = (Resolve-Path $script:InstallDir).Path
  }
  return ($want -and ($root -eq $want))
}

function Get-TsContentSha256 {
  param([string]$Root)
  $excludeNames = @('.env', '.env.local', '.studio-update-check', '.studio-state.json', '.studio-consumer', '.studio-update-cache.json', 'compose.override.yml', 'docker-compose.override.yml')
  $excludeDirNames = @('data', '.git', '.cursor', '.plan', '.venv', 'node_modules', '__pycache__')
  $files = Get-ChildItem -Path $Root -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object {
    $rel = $_.FullName.Substring($Root.Length).TrimStart('\', '/')
    $parts = $rel -split '[\\/]'
    $skip = $false
    foreach ($p in $parts) {
      if ($excludeDirNames -contains $p) { $skip = $true; break }
    }
    if ($skip) { return $false }
    if ($excludeNames -contains $_.Name) { return $false }
    if ($rel -like 'scripts\.bin\*') { return $false }
    return $true
  } | Sort-Object FullName

  $lines = New-Object System.Collections.Generic.List[string]
  foreach ($f in $files) {
    $hash = (Get-FileHash -Algorithm SHA256 -Path $f.FullName).Hash.ToLowerInvariant()
    $rel = ($f.FullName.Substring($Root.Length).TrimStart('\', '/') -replace '\\', '/')
    $lines.Add("$hash  ./$rel")
  }
  $joined = ($lines -join "`n") + "`n"
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($joined)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    $digest = $sha.ComputeHash($bytes)
    return ([BitConverter]::ToString($digest) -replace '-', '').ToLowerInvariant()
  } finally {
    $sha.Dispose()
  }
}

function Sync-TsPayload {
  param([string]$Source, [string]$Destination)
  if (-not (Get-Command robocopy -ErrorAction SilentlyContinue)) {
    throw (Get-TsText err_robocopy)
  }
  # /PURGE removes obsolete app files; /XD /XF keep user data and local markers.
  $args = @(
    $Source, $Destination, '/E', '/PURGE',
    '/NFL', '/NDL', '/NJH', '/NJS', '/NP',
    '/XD', 'data', '.git',
    '/XF', '.env', '.env.local',
    '.studio-update-check', '.studio-update-cache.json',
    '.studio-state.json', '.studio-consumer',
    'compose.override.yml', 'docker-compose.override.yml'
  )
  & robocopy @args | Out-Null
  if ($LASTEXITCODE -ge 8) { throw (Get-TsText err_robocopy_code $LASTEXITCODE) }
  $global:LASTEXITCODE = 0
}

function Write-TsUpdateCache {
  param([string]$Status, [string]$RemoteVersion = "", [string]$ArchiveUrl = "")
  $cache = Get-TsUpdateCachePath
  $obj = @{
    checked_at = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    status = $Status
    remote_version = $RemoteVersion
    archive_url = $ArchiveUrl
  }
  ($obj | ConvertTo-Json) | ForEach-Object { Write-TsUtf8NoBom -Path $cache -Content ($_ + "`n") }
}

function Read-TsUpdateCache {
  $cache = Get-TsUpdateCachePath
  if (-not (Test-Path $cache)) { return $false }
  $script:UpdateRemoteVersion = Get-TsJsonValue -Path $cache -Key remote_version
  $script:UpdateRemoteArchive = Get-TsJsonValue -Path $cache -Key archive_url
  $script:UpdateStatus = Get-TsJsonValue -Path $cache -Key status
  return [bool]$script:UpdateStatus
}

function Test-TsUpdateAvailable {
  param([switch]$Force)
  $script:UpdateAvailable = $false
  $script:UpdateSummary = ""
  $script:UpdateStatus = "error"
  $script:UpdateRemoteVersion = ""
  $script:UpdateLocalVersion = ""
  $script:UpdateRemoteArchive = ""

  if (-not (Test-TsUpdatableInstall)) {
    $script:UpdateSummary = "Developer tree — self-update disabled (consumer install only)"
    $script:UpdateStatus = "unsupported"
    return "unsupported"
  }

  $script:UpdateLocalVersion = Get-TsLocalVersion
  if (-not $script:UpdateLocalVersion) { $script:UpdateLocalVersion = "0" }

  if (-not (Test-TsUpdateShouldFetch -Force:$Force)) {
    if (Read-TsUpdateCache) {
      if ($script:UpdateStatus -eq "available" -and $script:UpdateRemoteVersion -and ($script:UpdateRemoteVersion -ne $script:UpdateLocalVersion)) {
        $script:UpdateAvailable = $true
        $script:UpdateSummary = "Update $($script:UpdateLocalVersion) → $($script:UpdateRemoteVersion)"
        return "available"
      }
      if ($script:UpdateStatus -eq "up_to_date" -or ($script:UpdateRemoteVersion -eq $script:UpdateLocalVersion)) {
        $script:UpdateSummary = "Up to date ($($script:UpdateLocalVersion))"
        $script:UpdateStatus = "up_to_date"
        return "up_to_date"
      }
    }
  }

  $url = Get-TsVersionManifestUrl
  try {
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("ts-ver-" + [guid]::NewGuid().ToString() + ".json")
    Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing -TimeoutSec 30
    Set-TsUpdateStamp
    $script:UpdateRemoteVersion = Get-TsJsonValue -Path $tmp -Key version
    $script:UpdateRemoteArchive = Get-TsJsonValue -Path $tmp -Key archive_url_zip
    if (-not $script:UpdateRemoteArchive) {
      $script:UpdateRemoteArchive = Get-TsJsonValue -Path $tmp -Key archive_url
    }
    Remove-Item -Force $tmp -ErrorAction SilentlyContinue
  } catch {
    $script:UpdateSummary = "Could not reach version manifest (offline?)"
    $script:UpdateStatus = "error"
    return "error"
  }

  if (-not $script:UpdateRemoteVersion) {
    $script:UpdateSummary = "Invalid version manifest"
    $script:UpdateStatus = "error"
    Write-TsUpdateCache -Status error
    return "error"
  }

  if ($script:UpdateRemoteVersion -eq $script:UpdateLocalVersion) {
    $script:UpdateSummary = "Up to date ($($script:UpdateLocalVersion))"
    $script:UpdateStatus = "up_to_date"
    Write-TsUpdateCache -Status up_to_date -RemoteVersion $script:UpdateRemoteVersion -ArchiveUrl $script:UpdateRemoteArchive
    return "up_to_date"
  }

  $script:UpdateAvailable = $true
  $script:UpdateSummary = "Update $($script:UpdateLocalVersion) → $($script:UpdateRemoteVersion)"
  $script:UpdateStatus = "available"
  Write-TsUpdateCache -Status available -RemoteVersion $script:UpdateRemoteVersion -ArchiveUrl $script:UpdateRemoteArchive
  return "available"
}

function Invoke-TsUpdate {
  $script:UpdateReexec = $false
  $plan = @(
    @{ Id = "check"; Label = (Get-TsText stage_check); Est = 15 }
    @{ Id = "stop"; Label = (Get-TsText stage_stop); Est = 25 }
    @{ Id = "download"; Label = (Get-TsText stage_download); Est = 40 }
    @{ Id = "verify"; Label = (Get-TsText stage_verify); Est = 30 }
    @{ Id = "apply"; Label = (Get-TsText stage_apply); Est = 25 }
    @{ Id = "rebuild"; Label = (Get-TsText stage_rebuild); Est = 120 }
  )

  Enter-TsProgressStage -Plan $plan -Id "check" -Status (Get-TsText status_read_remote)
  $root = Resolve-TsRoot
  if (-not $root) { throw (Get-TsText err_install_not_found) }
  Set-Location $root
  if (-not (Test-TsUpdatableInstall)) {
    throw (Get-TsText err_update_dev $script:InstallDir)
  }

  $status = Test-TsUpdateAvailable -Force
  switch ($status) {
    "up_to_date" {
      if ($script:TsProg) { $script:TsProg.Status = (Get-TsText status_up_to_date $script:UpdateLocalVersion) }
      Complete-TsProgress
      return
    }
    "available" { }
    "unsupported" { throw $script:UpdateSummary }
    default { throw (Get-TsText err_update_check $(if ($script:UpdateSummary) { $script:UpdateSummary } else { Get-TsText upd_unknown })) }
  }

  $remoteVer = $script:UpdateRemoteVersion
  $archiveUrl = $script:UpdateRemoteArchive
  if (-not $archiveUrl) {
    $archiveUrl = "https://codeload.github.com/DDoSKudya/task-studio/zip/refs/heads/$($script:RepoBranch)"
  }

  $wasRunning = ((Get-TsStackState) -eq "running")
  if ($wasRunning) {
    Enter-TsProgressStage -Plan $plan -Id "stop" -Status (Get-TsText status_stop_before_update)
    Assert-TsDocker
    if (-not (Ensure-TsStopped)) { throw (Get-TsText err_stop_before_update) }
  } else {
    Enter-TsProgressStage -Plan $plan -Id "stop" -Status (Get-TsText status_already_stopped)
  }

  Enter-TsProgressStage -Plan $plan -Id "download" -Status (Get-TsText status_downloading_ver $remoteVer)
  $work = Join-Path ([System.IO.Path]::GetTempPath()) ("task-studio-update-" + [guid]::NewGuid().ToString())
  New-Item -ItemType Directory -Path $work -Force | Out-Null
  $zipPath = Join-Path $work "src.zip"
  $extract = Join-Path $work "extract"
  New-Item -ItemType Directory -Path $extract -Force | Out-Null
  try {
    Invoke-WebRequest -Uri $archiveUrl -OutFile $zipPath -UseBasicParsing -TimeoutSec 600
    Expand-Archive -Path $zipPath -DestinationPath $extract -Force
    $payload = Get-ChildItem -Path $extract -Directory | Select-Object -First 1
    if (-not $payload -or -not (Test-Path (Join-Path $payload.FullName "studio-version.json"))) {
      throw (Get-TsText err_layout)
    }

    Enter-TsProgressStage -Plan $plan -Id "verify" -Status (Get-TsText status_compare_hash)
    $oldHash = Get-TsContentSha256 -Root $root
    $newHash = Get-TsContentSha256 -Root $payload.FullName
    if (-not $newHash) { throw (Get-TsText err_fingerprint) }

    $script:UpdateReexec = $true
    $envBefore = $null
    if (Test-Path (Join-Path $root ".env")) {
      $envBefore = (Get-Item (Join-Path $root ".env")).Length
    }

    if ($oldHash -eq $newHash) {
      Enter-TsProgressStage -Plan $plan -Id "apply" -Status (Get-TsText status_hash_same)
      Write-TsUpdateState -Version $remoteVer -ContentSha $newHash
      Set-TsConsumerMarker -Root $root
    } else {
      Enter-TsProgressStage -Plan $plan -Id "apply" -Status (Get-TsText status_replace_files)
      Sync-TsPayload -Source $payload.FullName -Destination $root
      if ($null -ne $envBefore -and -not (Test-Path (Join-Path $root ".env"))) {
        throw (Get-TsText err_env_gone)
      }
      $dataDir = Join-Path $root "data"
      if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }
      Write-TsUpdateState -Version $remoteVer -ContentSha $newHash
      Set-TsConsumerMarker -Root $root
    }
  } finally {
    Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
  }

  Enter-TsProgressStage -Plan $plan -Id "rebuild" -Status (Get-TsText status_rebuild)
  if (-not (Test-Path ".env")) {
    if ($script:TsProg) { $script:TsProg.Status = (Get-TsText status_no_env) }
    Complete-TsProgress
    return
  }
  Assert-TsDocker
  $profileArgs = Get-TsProfileArgs
  Invoke-TsCompose @($profileArgs + @("build"))
  if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw (Get-TsText err_build_update) }
  if (-not (Invoke-TsComposeUp -ProfileArgs $profileArgs)) {
    throw (Get-TsText err_up_update)
  }
  if (Wait-AppReady -Tries 90 -SleepSeconds 5) {
    Enter-TsProgressStage -Plan $plan -Id "rebuild" -Status (Get-TsText status_ui_ok)
  } else {
    Write-TsWarn (Get-TsText warn_ui_after_update $script:AppUiUrl)
  }
  try {
    Install-TaskStudioDesktopShortcuts -Root $root
  } catch {
    Write-TsWarn (Get-TsText warn_refresh_shortcuts $_.Exception.Message)
  }
  Complete-TsProgress
}
