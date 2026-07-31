#!/bin/sh
# Catalog container entrypoint: ensure packs dir, migrate once, then serve.
set -eu

PACKS_ROOT="${PACKS_ROOT:-/data/packs}"
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8002}"

echo "catalog-entrypoint: packs_root=${PACKS_ROOT} host=${HOST} port=${PORT}" >&2

if ! mkdir -p "${PACKS_ROOT}" 2>/dev/null; then
  echo "catalog-entrypoint: WARN cannot create ${PACKS_ROOT}, falling back to /tmp/packs" >&2
  PACKS_ROOT="/tmp/packs"
  export PACKS_ROOT
  mkdir -p "${PACKS_ROOT}"
fi

i=0
while [ "$i" -lt 12 ]; do
  if alembic upgrade head; then
    echo "catalog-entrypoint: migrations ok (attempt $((i + 1)))" >&2
    export CATALOG_MIGRATIONS_DONE=1
    break
  fi
  i=$((i + 1))
  if [ "$i" -ge 12 ]; then
    echo "catalog-entrypoint: migrations failed after ${i} attempts" >&2
    exit 1
  fi
  echo "catalog-entrypoint: migrations retry ${i}/12 in ${i}s…" >&2
  sleep "$i"
done

exec uvicorn app.main:app --host "${HOST}" --port "${PORT}"
