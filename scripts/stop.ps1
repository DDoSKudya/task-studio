#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$ComposeFile = "deploy/docker-compose.yml"

if (-not (Test-Path $ComposeFile)) {
  $homeRepo = Join-Path $HOME "task-studio"
  if (Test-Path (Join-Path $homeRepo $ComposeFile)) {
    Set-Location $homeRepo
  } else {
    throw "Не найден $ComposeFile. Запустите из корня репозитория."
  }
}

if (-not (Test-Path ".env")) {
  throw "Нет файла .env — нечего останавливать."
}

docker compose -f $ComposeFile --env-file .env --profile full --profile editor down
Write-Host "Стек остановлен."
