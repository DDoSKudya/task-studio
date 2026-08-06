#Requires -Version 5.1
param()

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$work = Join-Path ([System.IO.Path]::GetTempPath()) ("task-studio-update-" + [guid]::NewGuid().ToString())
$src = Join-Path $work "src"
$dst = Join-Path $work "dst"

New-Item -ItemType Directory -Path (Join-Path $src "app") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $src "data") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $dst "data\sub") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $dst ".git") -Force | Out-Null

try {
  Set-Content -Path (Join-Path $src "app\new.txt") -Value "new" -Encoding UTF8
  Set-Content -Path (Join-Path $src "data\.keep") -Value "payload-keep" -Encoding UTF8
  Set-Content -Path (Join-Path $src "studio-version.json") -Value '{"version":"1.0.1","channel":"develop","repo":"repo","ref":"develop","archive_url":"x","archive_url_zip":"y"}' -Encoding UTF8
  Set-Content -Path (Join-Path $dst ".env") -Value "keep-env" -Encoding UTF8
  Set-Content -Path (Join-Path $dst ".env.local") -Value "keep-env-local" -Encoding UTF8
  Set-Content -Path (Join-Path $dst "data\sub\data.txt") -Value "keep-data" -Encoding UTF8
  Set-Content -Path (Join-Path $dst ".studio-state.json") -Value "keep-state" -Encoding UTF8
  Set-Content -Path (Join-Path $dst ".studio-consumer") -Value "keep-consumer" -Encoding UTF8
  Set-Content -Path (Join-Path $dst "compose.override.yml") -Value "keep-override" -Encoding UTF8
  Set-Content -Path (Join-Path $dst ".git\config") -Value "keep-git" -Encoding UTF8
  Set-Content -Path (Join-Path $dst "obsolete.txt") -Value "old" -Encoding UTF8
  Set-Content -Path (Join-Path $dst ".studio-update-cache.json") -Value '{"status":"available"}' -Encoding UTF8

  . (Join-Path $Root "scripts\lib\I18n.ps1")
  . (Join-Path $Root "scripts\lib\Ops.ps1")
  Sync-TsPayload -Source $src -Destination $dst

  $mustExist = @(
    "app\new.txt",
    ".env",
    ".env.local",
    "data\sub\data.txt",
    ".studio-state.json",
    ".studio-consumer",
    "compose.override.yml",
    ".git\config",
    ".studio-update-cache.json"
  )
  foreach ($rel in $mustExist) {
    if (-not (Test-Path (Join-Path $dst $rel))) {
      throw "missing preserved path: $rel"
    }
  }
  if (Test-Path (Join-Path $dst "obsolete.txt")) {
    throw "obsolete file survived update"
  }
  if (Test-Path (Join-Path $dst "data\data")) {
    throw "user data nested under data/data"
  }
  $dataText = Get-Content -LiteralPath (Join-Path $dst "data\sub\data.txt") -Raw
  if ($dataText -notmatch "keep-data") {
    throw "user data content lost"
  }

  $treeA = Join-Path $work "hash-a"
  $treeB = Join-Path $work "hash-b"
  New-Item -ItemType Directory -Path (Join-Path $treeA "app") -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $treeB "app") -Force | Out-Null
  Set-Content -Path (Join-Path $treeA "app\x.txt") -Value "same" -Encoding UTF8
  Set-Content -Path (Join-Path $treeB "app\x.txt") -Value "same" -Encoding UTF8
  Set-Content -Path (Join-Path $treeA ".env") -Value "secret" -Encoding UTF8
  Set-Content -Path (Join-Path $treeA ".studio-update-cache.json") -Value '{"status":"available"}' -Encoding UTF8
  $hashA = Get-TsContentSha256 -Root $treeA
  $hashB = Get-TsContentSha256 -Root $treeB
  if (-not $hashA -or ($hashA -ne $hashB)) {
    throw "content hash should ignore .env and update cache"
  }

  Write-Host "smoke-launcher-update.ps1: OK"
} finally {
  Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
