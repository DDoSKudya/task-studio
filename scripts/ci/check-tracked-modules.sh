#!/usr/bin/env bash
# Guard against .gitignore swallowing Python packages (e.g. domain/cache/, domain/packs/).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

fail() {
  printf 'check-tracked-modules: %s\n' "$*" >&2
  exit 1
}

required_paths=(
  services/integrations/app/domain/cache/__init__.py
  services/integrations/app/domain/cache/service.py
  services/integrations/app/domain/cache/parse.py
  services/integrations/app/domain/cache/upsert.py
  services/catalog/app/domain/packs/__init__.py
  services/catalog/app/domain/packs/types.py
  services/catalog/app/domain/packs/store/__init__.py
  services/catalog/app/domain/packs/store/upload.py
)

echo "==> required source files exist"
for path in "${required_paths[@]}"; do
  [[ -f "$path" ]] || fail "missing $path"
done

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "==> required paths are not gitignored"
  for path in "${required_paths[@]}"; do
    if git check-ignore -q "$path"; then
      fail "$path is ignored by git — fix .gitignore"
    fi
  done
  # Catch .gitignore holes before push (same as CI).
  echo "==> required paths are tracked in git"
  for path in "${required_paths[@]}"; do
    git ls-files --error-unmatch "$path" >/dev/null 2>&1 \
      || fail "$path is not tracked — git add it (check .gitignore)"
  done
fi

echo "==> import smoke (integrations domain.cache)"
shared="packages/python-common/src:packages/contracts:packages/integration-sdk"
PYTHONPATH="services/integrations:${shared}" \
  uv run python -c "from app.domain.cache import list_cached_courses, replace_external_courses"

echo "check-tracked-modules: OK"
