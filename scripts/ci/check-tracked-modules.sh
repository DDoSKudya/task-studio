#!/usr/bin/env bash
# Guard against .gitignore swallowing Python packages (e.g. domain/cache/).
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
  # On GitHub Actions, required paths must already be in the tree (catch .gitignore holes).
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "==> required paths are tracked in git"
    for path in "${required_paths[@]}"; do
      git ls-files --error-unmatch "$path" >/dev/null 2>&1 \
        || fail "$path is not tracked — add and commit it"
    done
  fi
fi

echo "==> import smoke (integrations domain.cache)"
shared="packages/python-common/src:packages/contracts:packages/integration-sdk"
PYTHONPATH="services/integrations:${shared}" \
  uv run python -c "from app.domain.cache import list_cached_courses, replace_external_courses"

echo "check-tracked-modules: OK"
