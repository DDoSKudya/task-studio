#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "check-compose: docker CLI missing — skip"
  exit 0
fi

echo "==> docker compose config (.env.example)"
docker compose \
  -f deploy/docker-compose.yml \
  --env-file .env.example \
  config >/dev/null

if [[ -f deploy/docker-compose.web-dev.yml ]]; then
  echo "==> docker compose config (+ web-dev overlay)"
  docker compose \
    -f deploy/docker-compose.yml \
    -f deploy/docker-compose.web-dev.yml \
    --env-file .env.example \
    config >/dev/null
fi

echo "check-compose: OK"
