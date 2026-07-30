#Requires -Version 5.1
# Console manager UI — Debian-dialog style, brand colors from tokens.css

$script:TsViolet = "DarkMagenta"
$script:TsGold = "Yellow"
$script:TsFg = "White"
$script:TsMuted = "DarkGray"
$script:TsOk = "Magenta"
$script:TsDanger = "Red"
$script:TsSelBg = "DarkMagenta"
$script:TsSelFg = "Black"

function Use-TsSimpleUi {
  if ($env:TASK_STUDIO_SIMPLE_UI -eq "1") { return $true }
  if ($env:TASK_STUDIO_SIMPLE_UI -eq "0") { return $false }
  return ($PSVersionTable.PSEdition -ne "Core")
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

function Show-TsBanner([string]$Title = $(Get-TsText app_title)) { }

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
  if (-not $Footer) { $Footer = Get-TsText menu_footer_ps }
  $inner = $Width - 2
  $line = ("-" * $inner)
  $pad = (" " * $Left)

  for ($r = 0; $r -lt $Height; $r++) {
    if ($r -gt 0) { Write-Host "" }  # rely on Clear-Host + relative write via blank lines above
  }
  # Clear and position by printing leading blank lines then indented box
  Clear-Host
  for ($i = 0; $i -lt $Top; $i++) { Write-Host "" }

  Write-Host ($pad) -NoNewline
  Write-Host (Write-TsPad (" " + $Title) $Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg

  Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet

  # Body rows are drawn by caller between header and footer; this helper only chrome.
  # Caller uses Write-TsBoxLine.
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
}

function Read-TsChoice {
  param(
    [Parameter(Mandatory = $true)][string]$Prompt,
    [Parameter(Mandatory = $true)][hashtable[]]$Items
  )

  if (Use-TsSimpleUi) {
    while ($true) {
      Clear-Host
      Write-Host (Get-TsText app_title) -ForegroundColor $script:TsViolet
      Write-Host ""
      Write-Host $Prompt -ForegroundColor $script:TsGold
      Write-Host ""
      for ($i = 0; $i -lt $Items.Count; $i++) {
        Write-Host ("[{0}] {1}" -f ($i + 1), $Items[$i].Label) -ForegroundColor $script:TsFg
      }
      Write-Host ""
      $answer = Read-Host ((Get-TsText enter_continue) + " / number / q")
      if (-not $answer) { continue }
      if ($answer -match '^[Qq]$') { return $null }
      $picked = 0
      if ([int]::TryParse($answer, [ref]$picked)) {
        if ($picked -ge 1 -and $picked -le $Items.Count) {
          return $Items[$picked - 1].Value
        }
      }
    }
  }

  $selected = 0
  $count = $Items.Count
  $prefW = 58
  $prefH = $count + 9
  $prev = -1
  $chromeDrawn = $false
  $box = $null
  $listTop = 0

  while ($true) {
    $newBox = Get-TsCenterBox -PrefW $prefW -PrefH $prefH
    $resized = (-not $box) -or ($box.Top -ne $newBox.Top) -or ($box.Left -ne $newBox.Left) -or ($box.Width -ne $newBox.Width)
    $box = $newBox
    $inner = $box.Width - 2
    $line = ("-" * $inner)
    $pad = (" " * $box.Left)
    $listTop = $box.Top + 4

    if (-not $chromeDrawn -or $resized) {
      Clear-Host
      for ($i = 0; $i -lt $box.Top; $i++) { Write-Host "" }
      Write-Host ($pad) -NoNewline
      Write-Host (Write-TsPad ("  " + (Get-TsText app_title)) $box.Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
      Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
      Write-TsBoxLine -Left $box.Left -Width $box.Width -Text $Prompt -Style gold
      Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "" -Style muted
      for ($i = 0; $i -lt $count; $i++) {
        $mark = if ($i -eq $selected) { "> " } else { "  " }
        $style = if ($i -eq $selected) { "selected" } else { "muted" }
        Write-TsBoxLine -Left $box.Left -Width $box.Width -Text ($mark + $Items[$i].Label) -Style $style
      }
      Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
      Write-TsBoxLine -Left $box.Left -Width $box.Width -Text (Get-TsText menu_footer_ps) -Style muted
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
        $chromeDrawn = $false
        continue
      }
    }

    $key = $host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
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

# Destructive actions: user must type YES (exact).
function Confirm-TsYes {
  param([string]$Prompt = (Get-TsText type_yes_continue))
  Write-TsWarn (Get-TsText type_yes_hint)
  $answer = Read-Host $Prompt
  return ($answer -eq "YES")
}

function Wait-TsPause {
  param([string]$Message = $(Get-TsText press_enter_menu))
  if (Use-TsSimpleUi) {
    Write-Host ""
    [void](Read-Host $Message)
    return
  }
  $box = Get-TsCenterBox -PrefW 56 -PrefH 8
  $inner = $box.Width - 2
  $line = ("-" * $inner)
  $pad = (" " * $box.Left)
  Clear-Host
  for ($i = 0; $i -lt $box.Top; $i++) { Write-Host "" }
  Write-Host ($pad) -NoNewline
  Write-Host (Write-TsPad ("  " + (Get-TsText app_title)) $box.Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
  Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
  Write-TsBoxLine -Left $box.Left -Width $box.Width -Text $Message -Style gold
  Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "" -Style muted
  Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "[ Enter ]" -Style selected
  Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
  [void]$host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
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

function Invoke-TsProgress {
  param(
    [Parameter(Mandatory = $true)][string]$Title,
    [Parameter(Mandatory = $true)][scriptblock]$Action
  )

  if (Use-TsSimpleUi) {
    $script:TsProg = $null
    $script:TsProgressRefresh = $null
    Write-Host ""
    Write-Host ("== " + $Title + " ==") -ForegroundColor $script:TsViolet
    $ok = $true
    $errMsg = ""
    try {
      & $Action
    } catch {
      $ok = $false
      $errMsg = $_.Exception.Message
      if (-not $errMsg) { $errMsg = (Get-TsText cmd_failed_short) }
      Write-TsErr $errMsg
    } finally {
      $script:TsProgressRefresh = $null
      $script:TsProg = $null
    }
    if ($ok) {
      Write-TsOk (Get-TsText prog_completed)
    } else {
      Wait-TsPause
    }
    return
  }

  $logPath = [System.IO.Path]::GetTempFileName()
  $script:TsProg = @{
    Group = (Get-TsText prog_starting); Status = ""; PctLo = 0; PctHi = 5; StageEst = 10; LeftEst = 0
    StageT0 = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); Phase = "run"; Error = ""
  }
  $script:TsProgFp = ""
  $script:TsProgChromeDrawn = $false
  $script:TsLastProgressPaint = 0
  $script:TsProgBox = $null

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
    $fp = "$($snap.Phase)|$($snap.Group)|$statusLine|$($snap.Pct)|$($snap.Error)|$eta|$spin"
    $now = [Environment]::TickCount
    if (-not $Force -and $fp -eq $script:TsProgFp -and (($now - $script:TsLastProgressPaint) -lt 200)) {
      return
    }
    $script:TsProgFp = $fp
    $script:TsLastProgressPaint = $now

    $box = Get-TsCenterBox -PrefW 64 -PrefH 16
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
      Write-Host (Write-TsPad ("  " + (Get-TsText app_title) + " · " + $Title) $box.Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
      Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
      $script:TsProgChromeDrawn = $true
      $script:TsProgContentTop = $box.Top + 2
    }

    # Overwrite content in place (no Clear-Host) to avoid flicker.
    try {
      $raw = $Host.UI.RawUI
      $row = [Math]::Max(0, $box.Top + 2)
      $col = [Math]::Max(0, $box.Left)
      $lines = @(
        @{ T = ""; S = "muted" }
        @{ T = $snap.Group; S = "gold" }
        @{ T = $statusLine; S = "muted" }
        @{ T = ""; S = "muted" }
        @{ T = ("[" + $bar + "] " + $snap.Pct + "%"); S = "selected" }
        @{ T = $eta; S = "muted" }
        @{ T = ""; S = "muted" }
      )
      if ($snap.Phase -eq "error") {
        $lines += @{ T = (Get-TsText prog_error_label); S = "danger" }
        $lines += @{ T = $(if ($snap.Error) { $snap.Error } else { Get-TsText prog_unknown_error }); S = "danger" }
      } elseif ($snap.Phase -eq "done") {
        $lines += @{ T = (Get-TsText prog_completed); S = "ok" }
        $lines += @{ T = ""; S = "muted" }
      } else {
        $lines += @{ T = (Get-TsText prog_details_ps); S = "muted" }
        $lines += @{ T = ""; S = "muted" }
      }
      for ($i = 0; $i -lt $lines.Count; $i++) {
        $raw.CursorPosition = New-Object System.Management.Automation.Host.Coordinates $col, ($row + $i)
        Write-TsBoxLine -Left 0 -Width $box.Width -Text $lines[$i].T -Style $lines[$i].S
      }
      $raw.CursorPosition = New-Object System.Management.Automation.Host.Coordinates $col, ($row + $lines.Count)
      Write-Host ($pad.Substring(0, [Math]::Min($pad.Length, 0)) + "+" + $line + "+") -ForegroundColor $script:TsViolet
    } catch {
      # Fallback: rare hosts without RawUI — one clear only when forced.
      if ($Force) {
        Clear-Host
        for ($i = 0; $i -lt $box.Top; $i++) { Write-Host "" }
        Write-Host ($pad) -NoNewline
        Write-Host (Write-TsPad ("  " + (Get-TsText app_title) + " · " + $Title) $box.Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
        Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
        Write-TsBoxLine -Left $box.Left -Width $box.Width -Text $snap.Group -Style gold
        Write-TsBoxLine -Left $box.Left -Width $box.Width -Text $statusLine -Style muted
        Write-TsBoxLine -Left $box.Left -Width $box.Width -Text ("[" + $bar + "] " + $snap.Pct + "%") -Style selected
        Write-TsBoxLine -Left $box.Left -Width $box.Width -Text $eta -Style muted
      }
    }
  }

  Show-ProgressPanel -Force
  $script:TsLogFile = $logPath
  $script:TsLogQuiet = $true
  $script:TsProgressRefresh = { Show-ProgressPanel -Force }
  $ok = $true
  $errMsg = ""
  try {
    & $Action *>&1 | ForEach-Object {
      $line = ("$_").TrimEnd()
      if ($line) { Add-Content -Path $logPath -Value $line -Encoding utf8 }
      Show-ProgressPanel -Force
    }
  } catch {
    $ok = $false
    $errMsg = $_.Exception.Message
    Add-Content -Path $logPath -Value ("x " + $errMsg) -Encoding utf8
    Fail-TsProgress $errMsg
  } finally {
    $script:TsLogFile = $null
    $script:TsLogQuiet = $false
    $script:TsProgressRefresh = $null
  }

  if ($ok) {
    if (-not $script:TsProg -or $script:TsProg.Phase -ne "done") { Complete-TsProgress }
  } else {
    if (-not $errMsg -and (Test-Path $logPath)) {
      $hit = Get-Content $logPath -ErrorAction SilentlyContinue |
        Where-Object { $_ -match '(?i)error:|failed|fatal|denied|cannot |not found' } |
        Select-Object -Last 1
      if ($hit) { $errMsg = [string]$hit }
    }
    if (-not $errMsg) { $errMsg = (Get-TsText cmd_failed_short) }
    Fail-TsProgress $errMsg
  }
  Show-ProgressPanel -Force
  # Auto-return after 5s; any key skips.
  $deadline = [DateTime]::UtcNow.AddSeconds(5)
  while ([DateTime]::UtcNow -lt $deadline) {
    $remain = [Math]::Max(1, [int][Math]::Ceiling(($deadline - [DateTime]::UtcNow).TotalSeconds))
    if ($script:TsProg -and $script:TsProg.Phase -in @("done", "error")) {
      $script:TsProg.Status = (Get-TsText returning_footer $remain)
      $script:TsProgFp = ""
      Show-ProgressPanel
    }
    $hasKey = $false
    try { $hasKey = $Host.UI.RawUI.KeyAvailable } catch { $hasKey = $false }
    if ($hasKey) {
      try { [void]$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") } catch { }
      break
    }
    Start-Sleep -Milliseconds 250
  }
  Remove-Item -Force $logPath -ErrorAction SilentlyContinue
  $script:TsProg = $null
  $script:TsProgChromeDrawn = $false
}

# Back-compat
function Invoke-TsLogged {
  param([string]$Title, [scriptblock]$Action)
  Invoke-TsProgress -Title $Title -Action $Action
}

function Show-TsTextPanel {
  param(
    [string]$Title,
    [string[]]$Lines
  )
  if (Use-TsSimpleUi) {
    Clear-Host
    Write-Host $Title -ForegroundColor $script:TsViolet
    Write-Host ""
    foreach ($l in $Lines) {
      Write-Host $l -ForegroundColor $script:TsFg
    }
    Write-Host ""
    [void](Read-Host (Get-TsText press_enter_menu))
    return
  }
  $prefH = $Lines.Count + 8
  $box = Get-TsCenterBox -PrefW 64 -PrefH $prefH
  $inner = $box.Width - 2
  $line = ("-" * $inner)
  $pad = (" " * $box.Left)
  Clear-Host
  for ($i = 0; $i -lt $box.Top; $i++) { Write-Host "" }
  Write-Host ($pad) -NoNewline
  Write-Host (Write-TsPad ("  " + $Title) $box.Width) -ForegroundColor $script:TsSelFg -BackgroundColor $script:TsSelBg
  Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
  foreach ($l in $Lines) {
    Write-TsBoxLine -Left $box.Left -Width $box.Width -Text $l -Style muted
  }
  Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "" -Style muted
  Write-TsBoxLine -Left $box.Left -Width $box.Width -Text "[ Enter ]" -Style selected
  Write-Host ($pad + "+" + $line + "+") -ForegroundColor $script:TsViolet
  [void]$host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
