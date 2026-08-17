#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root

function Test-TsPsParseUtf8 {
  param([Parameter(Mandatory = $true)][string]$Path)
  $utf8 = New-Object System.Text.UTF8Encoding $false
  $bytes = [System.IO.File]::ReadAllBytes($Path)
  if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
    $text = $utf8.GetString($bytes, 3, $bytes.Length - 3)
  } else {
    $text = $utf8.GetString($bytes)
  }
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseInput(
    $text,
    [ref]$tokens,
    [ref]$errors
  )
  return $errors
}

Write-Host "==> PowerShell parse (Windows PowerShell, UTF-8)"
$files = @(
  "scripts\install.ps1",
  "scripts\install-bootstrap.ps1",
  "scripts\studio.ps1"
) + (Get-ChildItem -Path "scripts\lib" -Filter "*.ps1" -Recurse | ForEach-Object { $_.FullName })

$failed = $false
foreach ($path in $files) {
  $full = (Resolve-Path $path).Path
  $errors = Test-TsPsParseUtf8 -Path $full
  if ($errors -and $errors.Count -gt 0) {
    $failed = $true
    Write-Host "parse errors in $path"
    $errors | ForEach-Object { Write-Host $_ }
  }
}
if ($failed) {
  throw "PowerShell parse failed"
}

Write-Host "==> studio.cmd CRLF"
$cmdBytes = [System.IO.File]::ReadAllBytes((Join-Path $Root "scripts\studio.cmd"))
if ($cmdBytes.Length -eq 0) {
  throw "scripts\studio.cmd is empty"
}
$lf = 0
$crlf = 0
for ($i = 0; $i -lt $cmdBytes.Length; $i++) {
  if ($cmdBytes[$i] -eq 10) {
    $lf++
    if ($i -gt 0 -and $cmdBytes[$i - 1] -eq 13) {
      $crlf++
    }
  }
}
if ($lf -eq 0 -or $lf -ne $crlf) {
  throw "scripts\studio.cmd must use CRLF"
}

Write-Host "check-launcher.ps1: OK"
