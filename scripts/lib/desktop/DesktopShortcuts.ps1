#Requires -Version 5.1

function Get-DesktopPath {
  $p = [Environment]::GetFolderPath("Desktop")
  if ($p -and (Test-Path $p)) { return $p }
  $fallback = Join-Path $HOME "Desktop"
  if (-not (Test-Path $fallback)) { New-Item -ItemType Directory -Path $fallback | Out-Null }
  return $fallback
}

function Remove-TsZoneIdentifier {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path $Path)) { return }
  try { Unblock-File -Path $Path -ErrorAction SilentlyContinue } catch { }
  try {
    $ads = $Path + ":Zone.Identifier"
    if (Test-Path $ads) { Remove-Item -Force $ads -ErrorAction SilentlyContinue }
  } catch { }
  try {
    & cmd.exe /c "echo.>`"$Path`:Zone.Identifier`" 2>nul" | Out-Null
    Remove-Item -LiteralPath ($Path + ":Zone.Identifier") -Force -ErrorAction SilentlyContinue
  } catch { }
}

function Unlock-TaskStudioScripts {
  param([Parameter(Mandatory = $true)][string]$Root)
  $scriptDir = Join-Path $Root "scripts"
  if (-not (Test-Path $scriptDir)) { return }
  Get-ChildItem -Path $scriptDir -Recurse -Include *.ps1, *.cmd, *.bat -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-TsZoneIdentifier -Path $_.FullName
  }
  $brand = Join-Path $Root "docs\assets\brand"
  if (Test-Path $brand) {
    Get-ChildItem -Path $brand -File -ErrorAction SilentlyContinue | ForEach-Object {
      Remove-TsZoneIdentifier -Path $_.FullName
    }
  }
}

function Enable-TsScriptExecution {
  $notes = @()
  try {
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force -ErrorAction Stop
    $notes += "Process=Bypass"
  } catch {
    $notes += "Process policy locked"
  }
  foreach ($scope in @("CurrentUser")) {
    foreach ($pol in @("RemoteSigned", "Bypass", "Unrestricted")) {
      try {
        Set-ExecutionPolicy -Scope $scope -ExecutionPolicy $pol -Force -ErrorAction Stop
        $notes += "$scope=$pol"
        break
      } catch { }
    }
  }
  return ($notes -join "; ")
}

function Test-PowerShellRunnable {
  try {
    $machine = Get-ExecutionPolicy -Scope MachinePolicy -ErrorAction SilentlyContinue
    $user = Get-ExecutionPolicy -Scope UserPolicy -ErrorAction SilentlyContinue
    foreach ($p in @($machine, $user)) {
      if ($p -and $p -ne "Undefined" -and $p -ne "Bypass" -and $p -ne "Unrestricted" -and $p -ne "RemoteSigned") {
        Write-Host "Warning: Group Policy ExecutionPolicy is '$p'."
        Write-Host "  Desktop shortcut uses studio.cmd with -ExecutionPolicy Bypass."
        Write-Host "  If that is also blocked, open PowerShell and run:"
        Write-Host "    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned"
        Write-Host "  or ask IT to allow local scripts / Bypass for this folder."
        return $false
      }
    }
  } catch { }
  return $true
}

function New-TaskStudioShortcut {
  param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$CmdPath,
    [string]$Arguments = ""
  )
  $desktop = Get-DesktopPath
  $icon = Join-Path $Root "docs\assets\brand\task-studio.ico"
  if (-not (Test-Path $icon)) {
    $icon = Join-Path $Root "docs\assets\logo.png"
  }
  $lnkPath = Join-Path $desktop "$Name.lnk"
  $wsh = New-Object -ComObject WScript.Shell
  $sc = $wsh.CreateShortcut($lnkPath)
  $sc.TargetPath = $CmdPath
  if ($Arguments) { $sc.Arguments = $Arguments }
  $sc.WorkingDirectory = $Root
  $sc.WindowStyle = 1
  $sc.Description = $Name
  if (Test-Path $icon) {
    $sc.IconLocation = "$icon,0"
  }
  $sc.Save()
  Remove-TsZoneIdentifier -Path $lnkPath
  return $lnkPath
}

function Install-TaskStudioDesktopShortcuts {
  param([Parameter(Mandatory = $true)][string]$Root)
  $policyNote = Enable-TsScriptExecution
  Unlock-TaskStudioScripts -Root $Root
  [void](Test-PowerShellRunnable)
  if ($policyNote) {
    Write-Host "Execution policy: $policyNote"
  }

  $studioCmd = Join-Path $Root "scripts\studio.cmd"
  if (-not (Test-Path $studioCmd)) {
    throw "Missing studio.cmd under scripts\"
  }
  Remove-TsZoneIdentifier -Path $studioCmd

  $desktop = Get-DesktopPath
  $mainName = if (Get-Command Get-TsText -ErrorAction SilentlyContinue) {
    Get-TsText shortcut_main
  } else {
    "Task Studio Launcher"
  }
  $a = New-TaskStudioShortcut -Root $Root -Name $mainName -CmdPath $studioCmd
  foreach ($legacy in @(
      "Task Studio.lnk",
      "Task Studio - Uninstall.lnk",
      "Task Studio - Start.lnk",
      "Task Studio - Stop.lnk",
      "Task Studio Launcher - Uninstall.lnk",
      "Task Studio Launcher - Uninstall.lnk"
    )) {
    if ($legacy -eq ($mainName + ".lnk")) { continue }
    $p = Join-Path $desktop $legacy
    if (Test-Path $p) { Remove-Item -Force $p -ErrorAction SilentlyContinue }
  }
  if (Get-Command Get-TsText -ErrorAction SilentlyContinue) {
    $unName = Get-TsText shortcut_uninstall
    if ($unName -and $unName -ne $mainName) {
      $p = Join-Path $desktop ($unName + ".lnk")
      if (Test-Path $p) { Remove-Item -Force $p -ErrorAction SilentlyContinue }
    }
  }
  Write-Host ((Get-TsText shortcuts_created $desktop))
  Write-Host "  $a"
}

function Remove-TaskStudioDesktopShortcuts {
  $desktop = Get-DesktopPath
  $names = @(
    "Task Studio.lnk",
    "Task Studio Launcher.lnk",
    "Task Studio - Start.lnk",
    "Task Studio - Stop.lnk",
    "Task Studio - Uninstall.lnk",
    "Task Studio Launcher - Uninstall.lnk",
    "Task Studio Launcher - Uninstall.lnk"
  )
  if (Get-Command Get-TsText -ErrorAction SilentlyContinue) {
    $names += ((Get-TsText shortcut_main) + ".lnk")
    $names += ((Get-TsText shortcut_uninstall) + ".lnk")
  }
  foreach ($name in ($names | Select-Object -Unique)) {
    $path = Join-Path $desktop $name
    if (Test-Path $path) {
      Remove-Item -Force $path
    }
  }
}

function Get-TsStudioLaunchPaths {
  param([Parameter(Mandatory = $true)][string]$Root)
  $studioCmd = Join-Path $Root "scripts\studio.cmd"
  $studioPs1 = Join-Path $Root "scripts\studio.ps1"
  if (-not (Test-Path $studioPs1)) {
    throw "studio.ps1 not found under $Root\scripts"
  }
  return @{
    Cmd = $studioCmd
    Ps1 = $studioPs1
  }
}

function Get-TsPowerShellExe {
  foreach ($name in @("powershell.exe", "pwsh", "pwsh.exe")) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
  }
  throw "PowerShell executable was not found (powershell.exe / pwsh)."
}

function Test-TsWindowsLauncherHost {
  if ($env:OS -match 'Windows') { return $true }
  if (Get-Variable -Name IsWindows -ErrorAction SilentlyContinue) {
    try { if ($IsWindows) { return $true } } catch { }
  }
  return $false
}

function Start-TsStudioConsole {
  param(
    [Parameter(Mandatory = $true)][string]$Root,
    [object[]]$Arguments = @()
  )
  Enable-TsScriptExecution | Out-Null
  Unlock-TaskStudioScripts -Root $Root
  Set-Location $Root
  $paths = Get-TsStudioLaunchPaths -Root $Root
  $studioCmd = $paths.Cmd
  $studioPs1 = $paths.Ps1

  $argList = @($Arguments | ForEach-Object { $_ })
  $onWindows = Test-TsWindowsLauncherHost
  if ($onWindows -and (Test-Path $studioCmd) -and (Get-Command cmd.exe -ErrorAction SilentlyContinue)) {
    if ($argList.Count -gt 0) {
      & cmd.exe /c "`"$studioCmd`" $($argList -join ' ')"
    } else {
      & cmd.exe /c "`"$studioCmd`""
    }
    return $LASTEXITCODE
  }
  $psExe = Get-TsPowerShellExe
  & $psExe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $studioPs1 @argList
  return $LASTEXITCODE
}

function Start-TsStudioNewWindow {
  param(
    [Parameter(Mandatory = $true)][string]$Root,
    [object[]]$Arguments = @()
  )
  Enable-TsScriptExecution | Out-Null
  Unlock-TaskStudioScripts -Root $Root
  $paths = Get-TsStudioLaunchPaths -Root $Root
  $argList = @($Arguments | ForEach-Object { $_ })
  $onWindows = Test-TsWindowsLauncherHost
  if ($onWindows -and (Test-Path $paths.Cmd) -and (Get-Command cmd.exe -ErrorAction SilentlyContinue)) {
    if ($argList.Count -gt 0) {
      Start-Process -FilePath $paths.Cmd -ArgumentList ($argList -join " ") -WorkingDirectory $Root
    } else {
      Start-Process -FilePath $paths.Cmd -WorkingDirectory $Root
    }
    return
  }
  $psExe = Get-TsPowerShellExe
  $psArgs = @(
    "-NoLogo"
    "-NoProfile"
    "-ExecutionPolicy"
    "Bypass"
    "-File"
    $paths.Ps1
  )
  if ($argList.Count -gt 0) {
    $psArgs += $argList
  }
  Start-Process -FilePath $psExe -ArgumentList $psArgs -WorkingDirectory $Root
}
