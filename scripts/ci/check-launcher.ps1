#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root

Write-Host "==> PowerShell parse (Windows PowerShell)"
$files = @(
  "scripts\install.ps1",
  "scripts\studio.ps1"
) + (Get-ChildItem -Path "scripts\lib" -Filter "*.ps1" | ForEach-Object { $_.FullName })

$failed = $false
foreach ($path in $files) {
  $tokens = $null
  $errors = $null
  [void][System.Management.Automation.Language.Parser]::ParseFile(
    (Resolve-Path $path),
    [ref]$tokens,
    [ref]$errors
  )
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
