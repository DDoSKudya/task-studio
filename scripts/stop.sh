#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="deploy/docker-compose.yml"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  if [[ -f "$HOME/task-studio/$COMPOSE_FILE" ]]; then
    cd "$HOME/task-studio"
  else
    echo "Не найден $COMPOSE_FILE. Запустите из корня репозитория." >&2
    exit 1
  fi
fi

if [[ ! -f .env ]]; then
  echo "Нет файла .env — нечего останавливать." >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" --env-file .env --profile full --profile editor down
echo "Стек остановлен."
