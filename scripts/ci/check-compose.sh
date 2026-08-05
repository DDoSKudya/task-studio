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

if [[ -f deploy/docker-compose.ollama-gpu.yml ]]; then
  echo "==> docker compose config (+ ollama-gpu overlay)"
  docker compose \
    -f deploy/docker-compose.yml \
    -f deploy/docker-compose.ollama-gpu.yml \
    --env-file .env.example \
    --profile full \
    config >/dev/null
fi

if [[ -f deploy/profiles.json ]]; then
  echo "==> deploy/profiles.json"
  python3 - <<'PY'
import json
import sys
from pathlib import Path

path = Path("deploy/profiles.json")
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    print(f"invalid JSON: {exc}", file=sys.stderr)
    sys.exit(1)
if not isinstance(data, dict) or not data:
    print("profiles.json must be a non-empty object", file=sys.stderr)
    sys.exit(1)
profiles = data.get("profiles")
if not isinstance(profiles, dict) or not profiles:
    print("profiles.json must contain non-empty 'profiles' map", file=sys.stderr)
    sys.exit(1)
print(f"ok {len(profiles)} deploy profiles")
PY
fi

echo "check-compose: OK"
