#Requires -Version 5.1

$script:TsViolet = "DarkMagenta"
$script:TsGold = "Yellow"
$script:TsFg = "White"
$script:TsMuted = "DarkGray"
$script:TsOk = "Magenta"
$script:TsDanger = "Red"
$script:TsSelBg = "DarkMagenta"
$script:TsSelFg = "Black"
$script:TsConsoleFg = "Gray"
$script:TsConsoleBg = "Black"
$script:TsLibDir = $PSScriptRoot
if (-not $script:TsLibDir -and $MyInvocation.MyCommand.Path) {
  $script:TsLibDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
$script:TsLauncherVersion = $null
$script:TsLauncherBuild = $null
$script:TsLauncherVersionLoaded = $false

function Get-TsLauncherVersionPath {
  return (Join-Path $script:TsLibDir "..\launcher-version.json")
}

function Get-TsLauncherVersionInfo {
  if ($script:TsLauncherVersionLoaded) {
    return @{
      Version = [string]$script:TsLauncherVersion
      Build   = [string]$script:TsLauncherBuild
    }
  }
  $script:TsLauncherVersionLoaded = $true
  $script:TsLauncherVersion = ""
  $script:TsLauncherBuild = ""
  $path = Get-TsLauncherVersionPath
  if (Test-Path -LiteralPath $path) {
    try {
      $obj = Get-Content -Raw -LiteralPath $path -Encoding utf8 | ConvertFrom-Json
      if ($null -ne $obj.version) { $script:TsLauncherVersion = [string]$obj.version }
      if ($null -ne $obj.build) { $script:TsLauncherBuild = [string]$obj.build }
    } catch { }
  }
  return @{
    Version = [string]$script:TsLauncherVersion
    Build   = [string]$script:TsLauncherBuild
  }
}

function Get-TsChromeAppTitle {
  $base = "Task Studio Launcher"
  if (Get-Command Get-TsText -ErrorAction SilentlyContinue) {
    $base = Get-TsText app_title
  }
  $info = Get-TsLauncherVersionInfo
  if ($info.Version) {
    return ($base + " · " + $info.Version)
  }
  return $base
}

function Get-TsChromeFooter {
  param([string]$Base)
  $info = Get-TsLauncherVersionInfo
  if ($info.Build) {
    return ($Base + " · build " + $info.Build)
  }
  return $Base
}

function Reset-TsConsoleColors {
  try {
    [Console]::ResetColor()
  } catch { }
  try {
    $raw = $Host.UI.RawUI
    $raw.ForegroundColor = [ConsoleColor]::Gray
    $raw.BackgroundColor = [ConsoleColor]::Black
  } catch { }
}

function Test-TsRawUi {
  try {
    $null = $Host.UI.RawUI.WindowSize
    $null = $Host.UI.RawUI.CursorPosition
    return $true
  } catch {
    return $false
  }
}

function Use-TsSimpleUi {
  if ($env:TASK_STUDIO_SIMPLE_UI -eq "1") { return $true }
  if ($env:TASK_STUDIO_SIMPLE_UI -eq "0") { return $false }
  return -not (Test-TsRawUi)
}

function Write-TsLogLine([string]$Line) {
  if ($script:TsLogFile) {
    Add-Content -Path $script:TsLogFile -Value $Line -Encoding utf8 -ErrorAction SilentlyContinue
  }
}

function Write-TsInfo([string]$Message) {
  Write-TsLogLine ("> " + $Message)
  if (-not $script:TsLogQuiet) {
    Write-Host "> " -ForegroundColor $script:TsViolet -NoNewline
    Write-Host $Message -ForegroundColor $script:TsFg
  }
}

function Write-TsOk([string]$Message) {
  Write-TsLogLine ("+ " + $Message)
  if (-not $script:TsLogQuiet) {
    Write-Host "+ " -ForegroundColor $script:TsOk -NoNewline
    Write-Host $Message -ForegroundColor $script:TsFg
  }
}

function Write-TsWarn([string]$Message) {
  Write-TsLogLine ("! " + $Message)
  if (-not $script:TsLogQuiet) {
    Write-Host "! " -ForegroundColor $script:TsGold -NoNewline
    Write-Host $Message -ForegroundColor $script:TsFg
  }
}

function Write-TsErr([string]$Message) {
  Write-TsLogLine ("x " + $Message)
  if (-not $script:TsLogQuiet) {
    Write-Host "x " -ForegroundColor $script:TsDanger -NoNewline
    Write-Host $Message -ForegroundColor $script:TsFg
  }
}

function Show-TsBanner([string]$Title = $(Get-TsChromeAppTitle)) { }

function Get-TsTermSize {
  try {
    $ws = $Host.UI.RawUI.WindowSize
    return @{ Cols = [Math]::Max(40, [int]$ws.Width); Rows = [Math]::Max(12, [int]$ws.Height) }
  } catch {
    return @{ Cols = 80; Rows = 24 }
  }
}

function Get-TsCenterBox {
  param([int]$PrefW, [int]$PrefH)
  $sz = Get-TsTermSize
  $width = [Math]::Min($PrefW, $sz.Cols - 4)
  $height = [Math]::Min($PrefH, $sz.Rows - 2)
  if ($width -lt 36) { $width = 36 }
  if ($height -lt 7) { $height = 7 }
  $top = [Math]::Max(0, [int](($sz.Rows - $height) / 2))
  $left = [Math]::Max(0, [int](($sz.Cols - $width) / 2))
  return @{ Top = $top; Left = $left; Height = $height; Width = $width }
}

function Get-TsBoxPrefWidth {
  $sz = Get-TsTermSize
  $w = $sz.Cols - 4
  if ($w -lt 56) { $w = 56 }
  return $w
}

function Get-TsBoxPrefHeight {
  $sz = Get-TsTermSize
  $h = $sz.Rows - 2
  if ($h -lt 18) { $h = 18 }
  return $h
}

function Split-TsTextToWidth {
  param(
    [string]$Text,
    [int]$MaxWidth
  )
  if ($MaxWidth -lt 4) { $MaxWidth = 4 }
  if (-not $Text) { return @("") }
  $lines = New-Object System.Collections.Generic.List[string]
  $rest = $Text
  while ($rest.Length -gt $MaxWidth) {
    $breakAt = $MaxWidth
    $chunk = $rest.Substring(0, $MaxWidth)
    $spaceIdx = $chunk.LastIndexOf(' ')
    if ($spaceIdx -gt 0) { $breakAt = $spaceIdx }
    $line = $rest.Substring(0, $breakAt).TrimEnd()
    [void]$lines.Add($line)
    $rest = $rest.Substring($breakAt).TrimStart()
  }
  if ($rest.Length -gt 0) { [void]$lines.Add($rest) }
  return @($lines)
}

function Split-TsTextToWidthLimited {
  param(
    [string]$Text,
    [int]$MaxWidth,
    [int]$MaxLines
  )
  $lines = @(Split-TsTextToWidth -Text $Text -MaxWidth $MaxWidth)
  if ($MaxLines -le 0 -or $lines.Count -le $MaxLines) { return $lines }
  $trimmed = @($lines[0..($MaxLines - 1)])
  $lastIdx = $MaxLines - 1
  $last = $trimmed[$lastIdx]
  if ($last.Length -gt $MaxWidth) {
    if ($MaxWidth -le 3) {
      $trimmed[$lastIdx] = $last.Substring(0, $MaxWidth)
    } else {
      $trimmed[$lastIdx] = $last.Substring(0, $MaxWidth - 3) + "..."
    }
  }
  return $trimmed
}

function Write-TsWrappedBoxLines {
  param(
    [int]$Left,
    [int]$Width,
    [string]$Text,
    [ValidateSet("normal", "selected", "gold", "muted", "ok", "danger")]
    [string]$Style = "normal",
    [int]$MaxLines = 0
  )
  $inner = $Width - 4
  if ($inner -lt 4) { $inner = 4 }
  if ($MaxLines -gt 0) {
    $parts = @(Split-TsTextToWidthLimited -Text $Text -MaxWidth $inner -MaxLines $MaxLines)
  } else {
    $parts = @(Split-TsTextToWidth -Text $Text -MaxWidth $inner)
  }
  if ($parts.Count -eq 0) { $parts = @("") }
  foreach ($part in $parts) {
    Write-TsBoxLine -Left $Left -Width $Width -Text $part -Style $Style
  }
}

function Write-TsPad([string]$Text, [int]$Width) {
  if ($null -eq $Text) { $Text = "" }
  if ($Text.Length -gt $Width) {
    if ($Width -le 3) { return $Text.Substring(0, $Width) }
    return $Text.Substring(0, $Width - 3) + "..."
  }
  return $Text.PadRight($Width)
}

function Write-TsFrame {
  param(
    [int]$Top, [int]$Left, [int]$Height, [int]$Width,
    [string]$Title,
    [string]$Footer = ""
  )
  if (-not $Footer) { $Footer = Get-TsChromeFooter (Get-TsText menu_footer_ps) }
  $inner = $Width - 2
  $line = ("-" * $inner)
  $pad = (" " * $Left)

  for ($r = 0; $r -lt $Height; $r++) {
    if ($r -gt 0) { Write-Host "" }
  }
  Clear-Host
  for ($i = 0; $i -lt $Top; $i++) { Write-Host "" }

  Write-Host ($pad) -NoNewline
  Write-Host (Write-TsPad (" " + $Title) $Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg

  Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet

}

function Write-TsBoxLine {
  param(
    [int]$Left,
    [int]$Width,
    [string]$Text,
    [ValidateSet("normal", "selected", "gold", "muted", "ok", "danger")]
    [string]$Style = "normal"
  )
  $inner = $Width - 2
  $pad = (" " * $Left)
  $content = Write-TsPad (" " + $Text) $inner
  Write-Host ($pad + "|") -ForegroundColor $script:TsViolet -NoNewline
  switch ($Style) {
    "selected" { Write-Host $content -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg -NoNewline }
    "gold" { Write-Host $content -ForegroundColor $script:TsGold -NoNewline }
    "muted" { Write-Host $content -ForegroundColor $script:TsMuted -NoNewline }
    "ok" { Write-Host $content -ForegroundColor $script:TsOk -NoNewline }
    "danger" { Write-Host $content -ForegroundColor $script:TsDanger -NoNewline }
    default { Write-Host $content -ForegroundColor $script:TsFg -NoNewline }
  }
  Write-Host "|" -ForegroundColor $script:TsViolet
  Reset-TsConsoleColors
}

function Show-TsChoiceFallback {
  param(
    [Parameter(Mandatory = $true)][string]$Prompt,
    [Parameter(Mandatory = $true)][hashtable[]]$Items
  )
  Reset-TsConsoleColors
  $selected = 0
  $count = $Items.Count
  while ($true) {
    Clear-Host
    Write-Host ""
    Write-Host $Prompt -ForegroundColor $script:TsGold
    Write-Host ""
    for ($i = 0; $i -lt $count; $i++) {
      $mark = if ($i -eq $selected) { "> " } else { "  " }
      $num = $i + 1
      $line = ("{0}{1}. {2}" -f $mark, $num, $Items[$i].Label)
      if ($i -eq $selected) {
        Write-Host $line -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
        Reset-TsConsoleColors
      } else {
        Write-Host $line -ForegroundColor $script:TsMuted
      }
    }
    Write-Host ""
    Write-Host (Get-TsChromeFooter (Get-TsText menu_footer_ps)) -ForegroundColor $script:TsMuted
    try {
      $key = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } catch {
      return $Items[0].Value
    }
    $vk = [int]$key.VirtualKeyCode
    switch ($vk) {
      38 { $selected = ($selected - 1 + $count) % $count }
      40 { $selected = ($selected + 1) % $count }
      13 { return $Items[$selected].Value }
      32 { return $Items[$selected].Value }
      27 { return $null }
      81 { return $null }
      default {
        if ($vk -ge 49 -and $vk -le 57) {
          $idx = $vk - 49
          if ($idx -lt $count) { return $Items[$idx].Value }
        }
        if ($vk -ge 97 -and $vk -le 105) {
          $idx = $vk - 97
          if ($idx -lt $count) { return $Items[$idx].Value }
        }
      }
    }
  }
}

function Read-TsChoice {
  param(
    [Parameter(Mandatory = $true)][string]$Prompt,
    [Parameter(Mandatory = $true)][hashtable[]]$Items
  )

  Reset-TsConsoleColors

  if (Use-TsSimpleUi) {
    return (Show-TsChoiceFallback -Prompt $Prompt -Items $Items)
  }

  $selected = 0
  $count = $Items.Count
  $needH = $count + 9
  $prefW = Get-TsBoxPrefWidth
  $prefH = [Math]::Max($needH, (Get-TsBoxPrefHeight))
  $prev = -1
  $chromeDrawn = $false
  $box = $null
  $listTop = 0

  while ($true) {
    $prefW = Get-TsBoxPrefWidth
    $prefH = [Math]::Max($needH, (Get-TsBoxPrefHeight))
    $newBox = Get-TsCenterBox -PrefW $prefW -PrefH $prefH
    $resized = (-not $box) -or ($box.Top -ne $newBox.Top) -or ($box.Left -ne $newBox.Left) -or ($box.Width -ne $newBox.Width) -or ($box.Height -ne $newBox.Height)
    $box = $newBox
    $inner = $box.Width - 2
    $line = ("-" * $inner)
    $pad = (" " * $box.Left)
    $listTop = $box.Top + 4

    if (-not $chromeDrawn -or $resized) {
      Clear-Host
      for ($i = 0; $i -lt $box.Top; $i++) { Write-Host "" }
      Write-Host ($pad) -NoNewline
      Write-Host (Write-TsPad ("  " + (Get-TsChromeAppTitle)) $box.Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
      Reset-TsConsoleColors
      Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
      Write-TsBoxLine -Left $box.Left -Width $box.Width -Text $Prompt -Style gold
      Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "" -Style muted
      for ($i = 0; $i -lt $count; $i++) {
        $mark = if ($i -eq $selected) { "> " } else { "  " }
        $style = if ($i -eq $selected) { "selected" } else { "muted" }
        Write-TsBoxLine -Left $box.Left -Width $box.Width -Text ($mark + $Items[$i].Label) -Style $style
      }

      $bodyUsed = 2 + $count
      $bodyAvail = [Math]::Max(0, $box.Height - 4)
      for ($i = $bodyUsed; $i -lt $bodyAvail; $i++) {
        Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "" -Style muted
      }
      Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
      Write-TsBoxLine -Left $box.Left -Width $box.Width -Text (Get-TsChromeFooter (Get-TsText menu_footer_ps)) -Style muted
      $chromeDrawn = $true
      $prev = $selected
    } elseif ($prev -ne $selected) {
      try {
        $raw = $Host.UI.RawUI
        if ($prev -ge 0) {
          $raw.CursorPosition = New-Object System.Management.Automation.Host.Coordinates $box.Left, ($listTop + $prev)
          Write-TsBoxLine -Left 0 -Width $box.Width -Text ("  " + $Items[$prev].Label) -Style muted
        }
        $raw.CursorPosition = New-Object System.Management.Automation.Host.Coordinates $box.Left, ($listTop + $selected)
        Write-TsBoxLine -Left 0 -Width $box.Width -Text ("> " + $Items[$selected].Label) -Style selected
        $prev = $selected
      } catch {
        return (Show-TsChoiceFallback -Prompt $Prompt -Items $Items)
      }
    }

    try {
      $key = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    } catch {
      return (Show-TsChoiceFallback -Prompt $Prompt -Items $Items)
    }
    switch ($key.VirtualKeyCode) {
      38 { $selected = ($selected - 1 + $count) % $count }
      40 { $selected = ($selected + 1) % $count }
      13 { return $Items[$selected].Value }
      32 { return $Items[$selected].Value }
      27 { return $null }
      81 { return $null }
    }
  }
}

function Confirm-Ts {
  param([string]$Prompt = (Get-TsText confirm_continue))
  $pick = Read-TsChoice -Prompt $Prompt -Items @(
    @{ Value = "yes"; Label = (Get-TsText yes) }
    @{ Value = "no"; Label = (Get-TsText no) }
  )
  return ($pick -eq "yes")
}

function Confirm-TsDelete {
  param([string]$Prompt = (Get-TsText confirm_uninstall))
  $pick = Read-TsChoice -Prompt $Prompt -Items @(
    @{ Value = "delete"; Label = (Get-TsText action_delete) }
    @{ Value = "cancel"; Label = (Get-TsText action_cancel) }
  )
  return ($pick -eq "delete")
}

function Confirm-TsYes {
  param([string]$Prompt = (Get-TsText confirm_uninstall))
  return (Confirm-TsDelete -Prompt $Prompt)
}

function Clear-TsConsoleKeyBuffer {
  try {
    while ([Console]::KeyAvailable) {
      $null = [Console]::ReadKey($true)
    }
  } catch { }
}

function Test-TsConsumeKeyPress {
  try {
    if ([Console]::KeyAvailable) {
      $null = [Console]::ReadKey($true)
      return $true
    }
  } catch { }
  return $false
}

function Wait-TsAutoReturn {
  param(
    [int]$Seconds = 5,
    [scriptblock]$OnTick = $null
  )
  Clear-TsConsoleKeyBuffer
  $total = [Math]::Max(1, $Seconds)
  for ($left = $total; $left -ge 1; $left--) {
    if ($OnTick) {
      try { & $OnTick $left } catch { }
    }
    $sliceEnd = [DateTime]::UtcNow.AddSeconds(1)
    while ([DateTime]::UtcNow -lt $sliceEnd) {
      if (Test-TsConsumeKeyPress) { return }
      Start-Sleep -Milliseconds 100
    }
  }
}

function Wait-TsPause {
  param(
    [string]$Message = $(Get-TsText press_enter_menu),
    [int]$AutoSeconds = 5
  )
  Reset-TsConsoleColors
  if (Use-TsSimpleUi -or -not (Test-TsRawUi)) {
    Wait-TsAutoReturn -Seconds $AutoSeconds -OnTick {
      param([int]$Sec)
      Clear-Host
      Write-Host ""
      Write-Host $Message -ForegroundColor $script:TsGold
      Write-Host ""
      Write-Host (Get-TsText returning_footer $Sec) -ForegroundColor $script:TsMuted
      Write-Host ""
      Write-Host "[ Enter ]" -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
      Reset-TsConsoleColors
    }
    return
  }
  $box = Get-TsCenterBox -PrefW 56 -PrefH 9
  $inner = $box.Width - 2
  $line = ("-" * $inner)
  $pad = (" " * $box.Left)
  Wait-TsAutoReturn -Seconds $AutoSeconds -OnTick {
    param([int]$Sec)
    Clear-Host
    for ($i = 0; $i -lt $box.Top; $i++) { Write-Host "" }
    Write-Host ($pad) -NoNewline
    Write-Host (Write-TsPad ("  " + (Get-TsChromeAppTitle)) $box.Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
    Reset-TsConsoleColors
    Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
    Write-TsBoxLine -Left $box.Left -Width $box.Width -Text $Message -Style gold
    Write-TsBoxLine -Left $box.Left -Width $box.Width -Text (Get-TsText returning_footer $Sec) -Style muted
    Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "" -Style muted
    Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "[ Enter ]" -Style selected
    Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
  }
}

function Write-TsProgressBar([int]$Pct, [int]$Width) {
  if ($Width -lt 8) { $Width = 8 }
  if ($Pct -lt 0) { $Pct = 0 }
  if ($Pct -gt 100) { $Pct = 100 }
  $filled = [int]($Pct * $Width / 100)
  return ("#" * $filled) + ("-" * ($Width - $filled))
}

function Set-TsProgress {
  param(
    [string]$Group,
    [string]$Status = "",
    [int]$PctLo = 0,
    [int]$PctHi = 100,
    [int]$StageEst = 60,
    [int]$LeftEst = 0
  )
  $script:TsProg = @{
    Group = $Group
    Status = $Status
    PctLo = $PctLo
    PctHi = $PctHi
    StageEst = $StageEst
    LeftEst = $LeftEst
    StageT0 = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    Phase = "run"
    Error = ""
  }
  Write-TsProgSync
}

function Write-TsProgSync {
  if (-not $env:TS_PROG_SYNC) { return }
  if (-not $script:TsProg) { return }
  $p = $script:TsProg
  @(
    "Group=$($p.Group)"
    "Status=$($p.Status)"
    "PctLo=$($p.PctLo)"
    "PctHi=$($p.PctHi)"
    "StageEst=$($p.StageEst)"
    "LeftEst=$($p.LeftEst)"
    "StageT0=$($p.StageT0)"
    "Phase=$($p.Phase)"
    "Error=$($p.Error)"
  ) | Set-Content -Path $env:TS_PROG_SYNC -Encoding utf8 -Force
}

function Read-TsProgSync {
  param([string]$Path)
  if (-not $Path -or -not (Test-Path $Path)) { return }
  $map = @{}
  Get-Content -Path $Path -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') { $map[$Matches[1]] = $Matches[2] }
  }
  if (-not $map.ContainsKey("Phase")) { return }
  $script:TsProg = @{
    Group = $(if ($map.ContainsKey("Group")) { $map.Group } else { "" })
    Status = $(if ($map.ContainsKey("Status")) { $map.Status } else { "" })
    PctLo = $(if ($map.ContainsKey("PctLo")) { [int]$map.PctLo } else { 0 })
    PctHi = $(if ($map.ContainsKey("PctHi")) { [int]$map.PctHi } else { 5 })
    StageEst = $(if ($map.ContainsKey("StageEst")) { [int]$map.StageEst } else { 10 })
    LeftEst = $(if ($map.ContainsKey("LeftEst")) { [int]$map.LeftEst } else { 0 })
    StageT0 = $(if ($map.ContainsKey("StageT0")) { [int64]$map.StageT0 } else { [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() })
    Phase = $map.Phase
    Error = $(if ($map.ContainsKey("Error")) { $map.Error } else { "" })
  }
}

function Get-TsSpinnerFrame {
  $frames = @('|', '/', '-', '\')
  if (-not $script:TsSpinI) { $script:TsSpinI = 0 }
  $script:TsSpinI = ($script:TsSpinI + 1) % $frames.Count
  return $frames[$script:TsSpinI]
}

function Enter-TsProgressStage {
  param(
    [Parameter(Mandatory = $true)][hashtable[]]$Plan,
    [Parameter(Mandatory = $true)][string]$Id,
    [string]$Status = ""
  )
  $idx = -1
  for ($i = 0; $i -lt $Plan.Count; $i++) {
    if ($Plan[$i].Id -eq $Id) { $idx = $i; break }
  }
  if ($idx -lt 0) { return }
  $total = 0
  foreach ($s in $Plan) { $total += [int]$s.Est }
  if ($total -lt 1) { $total = 1 }
  $before = 0
  for ($i = 0; $i -lt $idx; $i++) { $before += [int]$Plan[$i].Est }
  $est = [int]$Plan[$idx].Est
  $after = $before + $est
  $left = 0
  for ($i = $idx + 1; $i -lt $Plan.Count; $i++) { $left += [int]$Plan[$i].Est }
  $lo = [int]($before * 100 / $total)
  $hi = [int]($after * 100 / $total)
  if ($hi -gt 99) { $hi = 99 }
  Set-TsProgress -Group $Plan[$idx].Label -Status $Status -PctLo $lo -PctHi $hi -StageEst $est -LeftEst $left
  if ($script:TsProgressRefresh) {
    & $script:TsProgressRefresh
  } elseif (-not $script:TsLogQuiet) {
    Write-TsInfo ("[" + $Plan[$idx].Label + "] " + $Status)
  }
}

function Get-TsProgressSnapshot {
  if (-not $script:TsProg) {
    return @{ Pct = 0; Eta = 0; Group = ""; Status = ""; Phase = "run"; Error = "" }
  }
  $p = $script:TsProg
  if ($p.Phase -eq "done") {
    return @{ Pct = 100; Eta = 0; Group = $p.Group; Status = $p.Status; Phase = "done"; Error = "" }
  }
  if ($p.Phase -eq "error") {
    return @{ Pct = $p.PctLo; Eta = 0; Group = $p.Group; Status = (Get-TsText prog_failed); Phase = "error"; Error = $p.Error }
  }
  $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  $elapsed = [Math]::Max(0, $now - [int]$p.StageT0)
  $est = [Math]::Max(1, [int]$p.StageEst)
  $frac = [Math]::Min(92, [int]($elapsed * 100 / $est))
  $pct = [int]($p.PctLo + ($p.PctHi - $p.PctLo) * $frac / 100)
  if ($pct -gt 99) { $pct = 99 }
  $remain = [Math]::Max(0, $est - $elapsed) + [int]$p.LeftEst
  return @{ Pct = $pct; Eta = $remain; Group = $p.Group; Status = $p.Status; Phase = "run"; Error = "" }
}

function Format-TsEta([int]$Sec) {
  if ($Sec -lt 60) { return (Get-TsText prog_eta_sec $Sec) }
  if ($Sec -lt 3600) { return (Get-TsText prog_eta_min ([int](($Sec + 30) / 60))) }
  return (Get-TsText prog_eta_hm ([int]($Sec / 3600)) ([int](($Sec % 3600) / 60)))
}

function Complete-TsProgress {
  if ($script:TsProg) {
    $script:TsProg.Phase = "done"
    $script:TsProg.Group = (Get-TsText prog_done)
    $script:TsProg.Status = (Get-TsText prog_finished_ok)
    Write-TsProgSync
  }
}

function Fail-TsProgress([string]$Message) {
  if ($script:TsProg) {
    $script:TsProg.Phase = "error"
    $script:TsProg.Error = $Message
    $script:TsProg.Status = (Get-TsText prog_failed)
    Write-TsProgSync
  }
}

function Get-TsProgressLogPath {
  param([string]$Root = (Get-Location).Path)
  $dir = Join-Path $Root "data\logs"
  try {
    if (-not (Test-Path $dir)) {
      New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $probe = Join-Path $dir "studio-last.log"
    [System.IO.File]::OpenWrite($probe).Close()
    return $probe
  } catch {
    $fallback = Join-Path $env:LOCALAPPDATA "task-studio\logs"
    if (-not $env:LOCALAPPDATA) {
      $fallback = Join-Path $env:TEMP "task-studio-logs"
    }
    if (-not (Test-Path $fallback)) {
      New-Item -ItemType Directory -Path $fallback -Force | Out-Null
    }
    return (Join-Path $fallback "studio-last.log")
  }
}

function Test-TsProgressLogNoise([string]$Line) {
  if ([string]::IsNullOrWhiteSpace($Line)) { return $true }
  if (Test-TsProgressLogSignal $Line) { return $false }
  if ($Line -match '^#\d+') { return $true }
  if ($Line -match '^\s*-{3,}\s*$') { return $true }
  if ($Line -match '(?i)deprecated|warning:') { return $true }
  if ($Line -match '(?i)^\s*Image\s+\S+\s+(Building|Built|Pulling|Pulled)\b') { return $true }
  if ($Line -match '(?i)^exporting |^naming to |^writing image|^unpacking |^extracting |^loading layer|^transferring context|^sha256:|^CACHED$|^DONE \d') { return $true }
  return $false
}

function Test-TsProgressLogSignal([string]$Line) {
  return [bool]($Line -match '(?i)error:|\bERROR\b|fatal:|\bFATAL\b|failed to solve|failed to |exit code|Cannot connect|permission denied|no space|ENOSPC|not found|refused|timeout|deadlock|out of memory|OOMKilled|\bOOM\b|heap out of memory|JavaScript heap|killed process|signal: killed|ResourceExhausted|invalid reference|manifest unknown|unauthorized|authentication|TLS handshake|no such file|Target failed|buildx failed|compose.*failed|npm error|ELIFECYCLE')
}

function Get-TsProgressLogExcerpt {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [int]$MaxLines = 5
  )
  if (-not (Test-Path $Path)) { return @() }
  if ($MaxLines -lt 1) { $MaxLines = 5 }

  $cleaned = New-Object System.Collections.Generic.List[string]
  $rawLines = Get-Content -LiteralPath $Path -Tail 120 -ErrorAction SilentlyContinue
  if (-not $rawLines) { return @() }
  foreach ($raw in $rawLines) {
    $line = ([string]$raw) -replace '\x1b\[[0-9;?]*[a-zA-Z]', '' -replace '\r', ''
    $line = ($line -replace '\s+', ' ').Trim()
    if (Test-TsProgressLogNoise $line) { continue }
    [void]$cleaned.Add($line)
  }
  if ($cleaned.Count -eq 0) { return @() }

  $signalIdx = New-Object System.Collections.Generic.List[int]
  for ($i = 0; $i -lt $cleaned.Count; $i++) {
    if (Test-TsProgressLogSignal $cleaned[$i]) { [void]$signalIdx.Add($i) }
  }

  $start = 0
  $end = $cleaned.Count
  if ($signalIdx.Count -gt 0) {
    $last = $signalIdx[$signalIdx.Count - 1]
    $start = $last - $MaxLines + 1
    if ($start -lt 0) { $start = 0 }
    $end = $last + 1
    if (($end - $start) -gt $MaxLines) { $start = $end - $MaxLines }
  } else {
    $start = $cleaned.Count - $MaxLines
    if ($start -lt 0) { $start = 0 }
  }

  $out = @()
  for ($i = $start; $i -lt $end -and $i -lt $cleaned.Count -and $out.Count -lt $MaxLines; $i++) {
    $text = $cleaned[$i]
    if ($text.Length -gt 120) { $text = $text.Substring(0, 120) }
    $out += $text
  }
  return $out
}

function Get-TsProgressLogSummary {
  param([Parameter(Mandatory = $true)][string]$Path)
  $excerpt = @(Get-TsProgressLogExcerpt -Path $Path -MaxLines 5)
  if ($excerpt.Count -gt 0) { return $excerpt[$excerpt.Count - 1] }
  return ""
}

function Invoke-TsProgress {
  param(
    [Parameter(Mandatory = $true)][string]$Title,
    [Parameter(Mandatory = $true)][scriptblock]$Action
  )

  $root = (Get-Location).Path
  $logPath = Get-TsProgressLogPath -Root $root

  if (Use-TsSimpleUi) {
    Write-TsInfo ("[" + $Title + "] …")
    Write-TsInfo (Get-TsText prog_details $logPath)
    $script:TsLogQuiet = $true
    $script:TsLogFile = $logPath
    $ok = $true
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
      & $Action > $logPath 2>&1
    } catch {
      $ok = $false
      Write-TsErr $_.Exception.Message
      Add-Content -LiteralPath $logPath -Value ("x " + $_.Exception.Message) -Encoding utf8 -ErrorAction SilentlyContinue
    } finally {
      $ErrorActionPreference = $prevEap
      $script:TsLogQuiet = $false
      $script:TsLogFile = $null
    }
    if ($ok) { Write-TsOk (Get-TsText prog_completed) } else {
      Write-TsErr (Get-TsText prog_failed)
      $excerpt = @(Get-TsProgressLogExcerpt -Path $logPath -MaxLines 5)
      foreach ($el in $excerpt) { Write-TsErr $el }
      Write-TsInfo (Get-TsText prog_log_hint $logPath)
    }
    Wait-TsPause
    return
  }

  $work = Join-Path ([System.IO.Path]::GetTempPath()) ("ts-prog-" + [guid]::NewGuid().ToString())
  New-Item -ItemType Directory -Path $work -Force | Out-Null
  $syncPath = Join-Path $work "sync.txt"
  $rcPath = Join-Path $work "rc.txt"
  $actionPath = Join-Path $work "action.ps1"
  New-Item -ItemType File -Path $logPath -Force | Out-Null
  $enc = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($actionPath, $Action.ToString(), $enc)
  [System.IO.File]::WriteAllText($logPath, "", $enc)
  [System.IO.File]::WriteAllText(
    $syncPath,
    @(
      "Group=$(Get-TsText prog_starting)"
      "Status="
      "PctLo=0"
      "PctHi=5"
      "StageEst=10"
      "LeftEst=0"
      "StageT0=$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
      "Phase=run"
      "Error="
    ) -join "`n",
    $enc
  )

  $script:TsProg = @{
    Group = (Get-TsText prog_starting); Status = ""; PctLo = 0; PctHi = 5; StageEst = 10; LeftEst = 0
    StageT0 = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); Phase = "run"; Error = ""
  }
  $script:TsProgFp = ""
  $script:TsProgChromeDrawn = $false
  $script:TsLastProgressPaint = 0
  $script:TsProgBox = $null
  $script:TsProgressLogPath = $logPath

  function Show-ProgressPanel {
    param([switch]$Force)
    $snap = Get-TsProgressSnapshot
    $spin = ""
    $statusLine = $snap.Status
    if ($snap.Phase -eq "run") {
      $spin = Get-TsSpinnerFrame
      if ($statusLine) { $statusLine = "$spin  $statusLine" } else { $statusLine = $spin }
    }
    $eta = if ($snap.Phase -eq "error") { Get-TsText prog_eta_failed }
      elseif ($snap.Phase -eq "done") { Get-TsText prog_eta_done }
      elseif ($snap.Eta -le 0) { Get-TsText prog_eta_finishing }
      else {
        if ($snap.Eta -lt 60) { Format-TsEta ([int]([math]::Floor($snap.Eta / 10) * 10)) }
        else { Format-TsEta ([int]([math]::Floor($snap.Eta / 30) * 30)) }
      }
    $logHint = if ($snap.Phase -eq "error") {
      Get-TsText prog_log_hint $script:TsProgressLogPath
    } else {
      Get-TsText prog_details_ps $script:TsProgressLogPath
    }
    $excerpt = @()
    if ($snap.Phase -eq "error" -and $script:TsProgressLogPath) {
      $excerpt = @(Get-TsProgressLogExcerpt -Path $script:TsProgressLogPath -MaxLines 5)
      if ($excerpt.Count -eq 0 -and $snap.Error) { $excerpt = @($snap.Error) }
      if ($excerpt.Count -eq 0) { $excerpt = @((Get-TsText prog_unknown_error)) }
    }
    $fp = "$($snap.Phase)|$($snap.Group)|$statusLine|$($snap.Pct)|$($snap.Error)|$eta|$spin|$logHint|$($excerpt -join '`')"
    $now = [Environment]::TickCount
    if (-not $Force -and $fp -eq $script:TsProgFp -and (($now - $script:TsLastProgressPaint) -lt 400)) {
      return
    }
    $script:TsProgFp = $fp
    $script:TsLastProgressPaint = $now

    $prefW = Get-TsBoxPrefWidth
    $prefH = Get-TsBoxPrefHeight
    $box = Get-TsCenterBox -PrefW $prefW -PrefH $prefH
    $resized = $false
    if ($script:TsProgBox) {
      $resized = (
        $script:TsProgBox.Top -ne $box.Top -or
        $script:TsProgBox.Left -ne $box.Left -or
        $script:TsProgBox.Width -ne $box.Width -or
        $script:TsProgBox.Height -ne $box.Height
      )
    }
    if ($resized) {
      $script:TsProgChromeDrawn = $false
      $Force = $true
    }
    $script:TsProgBox = $box
    $inner = $box.Width - 2
    $line = ("-" * $inner)
    $pad = (" " * $box.Left)
    $barW = [Math]::Max(10, $box.Width - 14)
    $bar = Write-TsProgressBar -Pct $snap.Pct -Width $barW

    if (-not $script:TsProgChromeDrawn -or $Force) {
      Clear-Host
      for ($i = 0; $i -lt $box.Top; $i++) { Write-Host "" }
      Write-Host ($pad) -NoNewline
      Write-Host (Write-TsPad ("  " + (Get-TsChromeAppTitle) + " · " + $Title) $box.Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
      Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
      $script:TsProgChromeDrawn = $true
      $script:TsProgContentTop = $box.Top + 2
    }

    $inner = $box.Width - 4
    if ($inner -lt 4) { $inner = 4 }
    $statusMax = if ($box.Height -lt 18) { 2 } else { 3 }
    $logMax = if ($box.Height -lt 18) { 1 } else { 2 }
    $excerptMax = if ($box.Height -lt 18) { 2 } else { 3 }

    try {
      $raw = $Host.UI.RawUI
      $row = [Math]::Max(0, $box.Top + 2)
      $col = [Math]::Max(0, $box.Left)
      $lines = @(
        @{ T = ""; S = "muted" }
        @{ T = $snap.Group; S = "gold" }
      )
      foreach ($sl in (Split-TsTextToWidthLimited -Text $statusLine -MaxWidth $inner -MaxLines $statusMax)) {
        $lines += @{ T = $sl; S = "muted" }
      }
      $lines += @{ T = ""; S = "muted" }
      $lines += @{ T = ("[" + $bar + "] " + $snap.Pct + "%"); S = "selected" }
      $lines += @{ T = $eta; S = "muted" }
      $lines += @{ T = ""; S = "muted" }
      if ($snap.Phase -eq "error") {
        $lines += @{ T = (Get-TsText prog_error_label); S = "danger" }
        $ei = 0
        foreach ($el in $excerpt) {
          if ($ei -ge $excerptMax) { break }
          foreach ($wl in (Split-TsTextToWidthLimited -Text $el -MaxWidth $inner -MaxLines 2)) {
            $lines += @{ T = $wl; S = "danger" }
          }
          $ei++
        }
        foreach ($ll in (Split-TsTextToWidthLimited -Text $logHint -MaxWidth $inner -MaxLines $logMax)) {
          $lines += @{ T = $ll; S = "muted" }
        }
      } elseif ($snap.Phase -eq "done") {
        $lines += @{ T = (Get-TsText prog_completed); S = "ok" }
        foreach ($ll in (Split-TsTextToWidthLimited -Text $logHint -MaxWidth $inner -MaxLines $logMax)) {
          $lines += @{ T = $ll; S = "muted" }
        }
      } else {
        foreach ($ll in (Split-TsTextToWidthLimited -Text $logHint -MaxWidth $inner -MaxLines $logMax)) {
          $lines += @{ T = $ll; S = "muted" }
        }
      }
      $bodyMax = [Math]::Max(6, $box.Height - 6)
      while ($lines.Count -lt $bodyMax) {
        $lines += @{ T = ""; S = "muted" }
      }
      if ($lines.Count -gt $bodyMax) {
        $lines = @($lines[0..($bodyMax - 1)])
      }
      for ($i = 0; $i -lt $lines.Count; $i++) {
        $raw.CursorPosition = New-Object System.Management.Automation.Host.Coordinates $col, ($row + $i)
        Write-TsBoxLine -Left 0 -Width $box.Width -Text $lines[$i].T -Style $lines[$i].S
      }
      $raw.CursorPosition = New-Object System.Management.Automation.Host.Coordinates $col, ($row + $lines.Count)
      Write-Host ("+" + $line + "+") -ForegroundColor $script:TsViolet
    } catch {
      if ($Force) {
        Clear-Host
        for ($i = 0; $i -lt $box.Top; $i++) { Write-Host "" }
        Write-Host ($pad) -NoNewline
        Write-Host (Write-TsPad ("  " + (Get-TsChromeAppTitle) + " · " + $Title) $box.Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
        Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
        Write-TsBoxLine -Left $box.Left -Width $box.Width -Text $snap.Group -Style gold
        Write-TsWrappedBoxLines -Left $box.Left -Width $box.Width -Text $statusLine -Style muted -MaxLines $statusMax
        Write-TsBoxLine -Left $box.Left -Width $box.Width -Text ("[" + $bar + "] " + $snap.Pct + "%") -Style selected
        Write-TsBoxLine -Left $box.Left -Width $box.Width -Text $eta -Style muted
        if ($snap.Phase -eq "error") {
          Write-TsBoxLine -Left $box.Left -Width $box.Width -Text (Get-TsText prog_error_label) -Style danger
          $ei = 0
          foreach ($el in $excerpt) {
            if ($ei -ge $excerptMax) { break }
            Write-TsWrappedBoxLines -Left $box.Left -Width $box.Width -Text $el -Style danger -MaxLines 2
            $ei++
          }
        }
        Write-TsWrappedBoxLines -Left $box.Left -Width $box.Width -Text $logHint -Style muted -MaxLines $logMax
      }
    }
  }

  Show-ProgressPanel -Force

  $worker = Join-Path $script:TsLibDir "../progress/ProgressWorker.ps1"
  if (-not (Test-Path $worker)) {
    throw "ProgressWorker.ps1 not found next to Ui.ps1"
  }
  $proc = Start-Process -FilePath "powershell.exe" -ArgumentList (
    "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$worker`" " +
    "-Root `"$root`" -SyncPath `"$syncPath`" -LogPath `"$logPath`" " +
    "-RcPath `"$rcPath`" -ActionPath `"$actionPath`""
  ) -WorkingDirectory $root -WindowStyle Hidden -PassThru

  while (-not $proc.HasExited) {
    Read-TsProgSync -Path $syncPath
    Show-ProgressPanel
    Start-Sleep -Milliseconds 250
  }
  try { $proc.Refresh() } catch { }
  Read-TsProgSync -Path $syncPath

  $exitCode = $proc.ExitCode
  $reexec = $false
  $uninstallExit = $false
  if (Test-Path $rcPath) {
    Get-Content -LiteralPath $rcPath -ErrorAction SilentlyContinue | ForEach-Object {
      if ($_ -match '^ExitCode=(.*)$') {
        $parsed = 0
        if ([int]::TryParse($Matches[1], [ref]$parsed)) { $exitCode = $parsed }
      }
      if ($_ -match '^Reexec=1$') { $reexec = $true }
      if ($_ -match '^UninstallExit=1$') { $uninstallExit = $true }
    }
  }
  $script:UpdateReexec = $reexec
  if ($uninstallExit) { $script:UninstallExit = $true }
  if (Test-TsUninstallShouldExit -Root $root) { $script:UninstallExit = $true }

  if ($exitCode -ne 0) {
    if (-not $script:TsProg -or $script:TsProg.Phase -ne "error") {
      $errMsg = ""
      if (Test-Path $logPath) {
        $errMsg = Get-TsProgressLogSummary -Path $logPath
      }
      if (-not $errMsg -and $script:TsProg -and $script:TsProg.Error) { $errMsg = $script:TsProg.Error }
      if (-not $errMsg) { $errMsg = (Get-TsText cmd_failed_short) }
      Fail-TsProgress $errMsg
    }
  } elseif (-not $script:TsProg -or $script:TsProg.Phase -notin @("done", "error")) {
    Complete-TsProgress
  }

  Show-ProgressPanel -Force
  Wait-TsAutoReturn -Seconds 5 -OnTick {
    param([int]$Sec)
    if ($script:TsProg -and $script:TsProg.Phase -in @("done", "error")) {
      $script:TsProg.Status = (Get-TsText returning_footer $Sec)
      $script:TsProgFp = ""
      Show-ProgressPanel -Force
    }
  }
  Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
  $script:TsProg = $null
  $script:TsProgChromeDrawn = $false
  $script:TsProgressLogPath = $null
  Reset-TsConsoleColors
  Clear-Host
}

function Invoke-TsLogged {
  param([string]$Title, [scriptblock]$Action)
  Invoke-TsProgress -Title $Title -Action $Action
}

function Show-TsTextPanel {
  param(
    [string]$Title,
    [string[]]$Lines
  )
  Reset-TsConsoleColors
  if (Use-TsSimpleUi) {
    Clear-Host
    Write-Host ""
    Write-Host $Title -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
    Reset-TsConsoleColors
    foreach ($l in $Lines) {
      if ($l) { Write-Host $l -ForegroundColor $script:TsMuted } else { Write-Host "" }
    }
    Write-Host ""
    Write-Host "[ Enter ]" -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
    Reset-TsConsoleColors
    try {
      while ($true) {
        $key = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        if ([int]$key.VirtualKeyCode -in @(13, 32, 27)) { break }
      }
    } catch { }
    return
  }
  $prefH = $Lines.Count + 8
  $prefW = Get-TsBoxPrefWidth
  $box = Get-TsCenterBox -PrefW $prefW -PrefH $prefH
  $inner = $box.Width - 2
  $line = ("-" * $inner)
  $pad = (" " * $box.Left)
  Clear-Host
  for ($i = 0; $i -lt $box.Top; $i++) { Write-Host "" }
  Write-Host ($pad) -NoNewline
  Write-Host (Write-TsPad ("  " + $Title) $box.Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
  Reset-TsConsoleColors
  Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
  foreach ($l in $Lines) {
    Write-TsWrappedBoxLines -Left $box.Left -Width $box.Width -Text $l -Style muted
  }
  Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "" -Style muted
  Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "[ Enter ]" -Style selected
  Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
  [void]$host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
