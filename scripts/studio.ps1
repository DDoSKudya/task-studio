#Requires -Version 5.1
param(
  [Parameter(Position = 0)][string]$Command = "",
  [switch]$Yes,
  [switch]$Purge,
  [switch]$Help
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootCandidate = Split-Path -Parent $ScriptDir

function Convert-TsPsTreeToUtf8Bom([string]$Root) {
  $utf8Bom = New-Object System.Text.UTF8Encoding $true
  $paths = @(
    (Join-Path $Root "scripts\install.ps1"),
    (Join-Path $Root "scripts\studio.ps1")
  ) + (Get-ChildItem -Path (Join-Path $Root "scripts\lib") -Filter "*.ps1" -File -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
  foreach ($path in ($paths | Select-Object -Unique)) {
    if (-not (Test-Path $path)) { continue }
    $bytes = [System.IO.File]::ReadAllBytes($path)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    if ($text.Length -gt 0 -and $text[0] -eq [char]0xFEFF) {
      $text = $text.Substring(1)
    }
    [System.IO.File]::WriteAllText($path, $text, $utf8Bom)
  }
}

Convert-TsPsTreeToUtf8Bom $RootCandidate
. (Join-Path $ScriptDir "lib\I18n.ps1")
. (Join-Path $ScriptDir "lib\Ui.ps1")
. (Join-Path $ScriptDir "lib\OpenApp.ps1")
. (Join-Path $ScriptDir "lib\DesktopShortcuts.ps1")
. (Join-Path $ScriptDir "lib\Ops.ps1")

if (Get-Command Reset-TsConsoleColors -ErrorAction SilentlyContinue) {
  Reset-TsConsoleColors
}

if (Test-Path (Join-Path $RootCandidate "deploy\docker-compose.yml")) {
  Set-Location $RootCandidate
}

function Show-TsHelp {
  Write-Host (Get-TsText usage_header) -ForegroundColor DarkMagenta
  Write-Host ""
  Write-Host (Get-TsText usage_body)
}

function Get-TsMenuItems {
  $state = Get-TsStackState
  $updateStatus = "nogit"
  try { $updateStatus = Test-TsUpdateAvailable } catch { $updateStatus = "error" }
  $items = @()
  switch ($state) {
    "missing" {
      $items += @{ Value = "install"; Label = (Get-TsText menu_install) }
    }
    "stopped" {
      $items += @{ Value = "start"; Label = (Get-TsText menu_start) }
      $items += @{ Value = "install"; Label = (Get-TsText menu_install_repair) }
      $items += @{ Value = "uninstall"; Label = (Get-TsText menu_uninstall) }
    }
    "running" {
      $items += @{ Value = "open"; Label = (Get-TsText menu_open) }
      $items += @{ Value = "heal"; Label = (Get-TsText menu_heal) }
      $items += @{ Value = "restart"; Label = (Get-TsText menu_restart) }
      $items += @{ Value = "install"; Label = (Get-TsText menu_install_repair) }
      $items += @{ Value = "stop"; Label = (Get-TsText menu_stop) }
      $items += @{ Value = "uninstall"; Label = (Get-TsText menu_uninstall) }
    }
  }
  if ($script:UpdateAvailable) {
    $items += @{ Value = "update"; Label = (Get-TsText menu_update) }
  } elseif ($updateStatus -ne "unsupported") {
    $items += @{ Value = "update"; Label = (Get-TsText menu_check_updates) }
  }
  $items += @{ Value = "help"; Label = (Get-TsText menu_help) }
  $items += @{ Value = "quit"; Label = (Get-TsText menu_quit) }
  return @{ State = $state; Items = $items; UpdateAvailable = [bool]$script:UpdateAvailable }
}

function Show-TsMenu {
  while ($true) {
    Reset-TsConsoleColors
    if (Test-Path (Join-Path $RootCandidate "deploy\docker-compose.yml")) {
      Set-Location $RootCandidate
    }
    $menu = Get-TsMenuItems
    $prompt = switch ($menu.State) {
      "missing" { (Get-TsText prompt_missing) }
      "stopped" { (Get-TsText prompt_stopped) }
      "running" { (Get-TsText prompt_running) }
      default { (Get-TsText prompt_default) }
    }
    if ($menu.UpdateAvailable) {
      $prompt = (Get-TsText prompt_update)
    }
    $pick = Read-TsChoice -Prompt $prompt -Items $menu.Items
    if (-not $pick -or $pick -eq "quit") {
      Write-TsInfo (Get-TsText bye)
      return
    }
    switch ($pick) {
      "start" {
        Invoke-TsProgress -Title (Get-TsText title_start) -Action { Invoke-TsStart }
      }
      "heal" {
        Invoke-TsProgress -Title (Get-TsText title_start) -Action { Invoke-TsStart }
      }
      "open" {
        Invoke-TsOpen
      }
      "stop" {
        Invoke-TsProgress -Title (Get-TsText title_stop) -Action { Invoke-TsStop }
      }
      "restart" {
        Invoke-TsProgress -Title (Get-TsText title_restart) -Action { Invoke-TsRestart }
      }
      "install" {
        Invoke-TsProgress -Title (Get-TsText title_install) -Action { Invoke-TsInstall }
      }
      "update" {
        $script:UpdateReexec = $false
        Invoke-TsProgress -Title (Get-TsText title_update) -Action { Invoke-TsUpdate }
        if ($script:UpdateReexec) {
          & (Join-Path $ScriptDir "studio.ps1")
          return
        }
      }
      "uninstall" {
        $consent = Confirm-TsUninstallConsent
        if ($consent) {
          if ($consent.Purge) { $env:TASK_STUDIO_UNINSTALL_PURGE = "1" } else { $env:TASK_STUDIO_UNINSTALL_PURGE = "0" }
          $env:TASK_STUDIO_UNINSTALL_YES = "1"
          Invoke-TsProgress -Title (Get-TsText title_uninstall) -Action {
            Invoke-TsUninstall -Yes -Purge:($env:TASK_STUDIO_UNINSTALL_PURGE -eq "1")
          }
          Remove-Item Env:TASK_STUDIO_UNINSTALL_YES -ErrorAction SilentlyContinue
          Remove-Item Env:TASK_STUDIO_UNINSTALL_PURGE -ErrorAction SilentlyContinue
          if ($script:UninstallExit -or (Test-TsUninstallShouldExit)) {
            Write-TsInfo (Get-TsText bye)
            return
          }
        }
      }
      "help" {
        Show-TsTextPanel -Title (Get-TsText help_title) -Lines @(
          (Get-TsText help_line_menu)
          (Get-TsText help_line_install)
          (Get-TsText help_line_start)
          (Get-TsText help_line_open)
          (Get-TsText help_line_stop)
          (Get-TsText help_line_restart)
          (Get-TsText help_line_update)
          (Get-TsText help_line_uninstall)
          ""
          (Get-TsText help_update_note1)
          (Get-TsText help_update_note2)
          (Get-TsText help_update_note3)
        )
      }
      default { throw "Unknown choice: $pick" }
    }
  }
}

if ($Help -or $Command -in @("help", "-h", "--help")) {
  Show-TsHelp
  exit 0
}

if ($Command.ToLowerInvariant() -eq "open") {
  Invoke-TsOpen
  exit 0
}

$known = @("", "install", "start", "heal", "stop", "restart", "update", "uninstall", "remove", "menu")
if ($Command -and ($known -notcontains $Command.ToLowerInvariant())) {
  Write-TsErr (Get-TsText unknown_command $Command)
  Show-TsHelp
  exit 1
}

try {
  Assert-TsDocker
} catch {
  Write-TsErr $_.Exception.Message
  exit 1
}

if (-not $Command) {
  Show-TsMenu
  exit 0
}

switch ($Command.ToLowerInvariant()) {
  "install" { Invoke-TsInstall }
  "start" { Invoke-TsStart }
  "heal" { Invoke-TsStart }
  "stop" { Invoke-TsStop }
  "restart" { Invoke-TsRestart }
  "update" {
    $script:UpdateReexec = $false
    Invoke-TsUpdate
    if ($script:UpdateReexec) {
      & (Join-Path $ScriptDir "studio.ps1")
      exit 0
    }
  }
  "uninstall" {
    $consent = Confirm-TsUninstallConsent -Yes:$Yes -Purge:$Purge
    if (-not $consent) { exit 0 }
    if ($consent.Purge) { $env:TASK_STUDIO_UNINSTALL_PURGE = "1" } else { $env:TASK_STUDIO_UNINSTALL_PURGE = "0" }
    $env:TASK_STUDIO_UNINSTALL_YES = "1"
    if (-not (Use-TsSimpleUi)) {
      Invoke-TsProgress -Title (Get-TsText title_uninstall) -Action {
        Invoke-TsUninstall -Yes -Purge:($env:TASK_STUDIO_UNINSTALL_PURGE -eq "1")
      }
    } else {
      Invoke-TsUninstall -Yes -Purge:$consent.Purge
    }
    Remove-Item Env:TASK_STUDIO_UNINSTALL_YES -ErrorAction SilentlyContinue
    Remove-Item Env:TASK_STUDIO_UNINSTALL_PURGE -ErrorAction SilentlyContinue
    if ($script:UninstallExit -or (Test-TsUninstallShouldExit)) { exit 0 }
  }
  "remove" {
    $consent = Confirm-TsUninstallConsent -Yes:$Yes -Purge:$Purge
    if (-not $consent) { exit 0 }
    if ($consent.Purge) { $env:TASK_STUDIO_UNINSTALL_PURGE = "1" } else { $env:TASK_STUDIO_UNINSTALL_PURGE = "0" }
    $env:TASK_STUDIO_UNINSTALL_YES = "1"
    if (-not (Use-TsSimpleUi)) {
      Invoke-TsProgress -Title (Get-TsText title_uninstall) -Action {
        Invoke-TsUninstall -Yes -Purge:($env:TASK_STUDIO_UNINSTALL_PURGE -eq "1")
      }
    } else {
      Invoke-TsUninstall -Yes -Purge:$consent.Purge
    }
    Remove-Item Env:TASK_STUDIO_UNINSTALL_YES -ErrorAction SilentlyContinue
    Remove-Item Env:TASK_STUDIO_UNINSTALL_PURGE -ErrorAction SilentlyContinue
    if ($script:UninstallExit -or (Test-TsUninstallShouldExit)) { exit 0 }
  }
  "menu" { Show-TsMenu }
  default {
    Write-TsErr (Get-TsText unknown_command $Command)
    Show-TsHelp
    exit 1
  }
}
