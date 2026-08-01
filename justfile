set dotenv-load := true
set export := true

DOCKER_BUILDKIT := "1"
COMPOSE_DOCKER_CLI_BUILD := "1"
COMPOSE_BAKE := "true"

compose := "docker compose -f deploy/docker-compose.yml --env-file .env"
compose_web_dev := "docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.web-dev.yml --env-file .env"
profile := "full"
editor_profile := "editor"
buildx_cache := "/tmp/task-studio-buildx-cache"

default:
    @just --list

up mode="":
    #!/usr/bin/env bash
    set -eo pipefail
    if [ -n "{{mode}}" ]; then export ORCHESTRATOR_MODE="{{mode}}"; fi
    profiles="--profile {{profile}}"
    if [ "${ORCHESTRATOR_MODE:-balancing}" != "power_saving" ]; then
      profiles="$profiles --profile {{editor_profile}}"
    fi
    export COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT:-4}"
    mkdir -p data/postgres data/redis data/rabbitmq data/packs data/meilisearch data/clickhouse data/minio data/ollama data/grafana data/prometheus data/piston/packages
    chmod -R a+rwX data/packs 2>/dev/null || true
    {{compose}} $profiles build
    {{compose}} $profiles up -d --force-recreate --remove-orphans
    echo "Stack rebuilt and running."

rebuild mode="":
    #!/usr/bin/env bash
    set -eo pipefail
    if [ -n "{{mode}}" ]; then
      just up "{{mode}}"
    else
      just up
    fi

start mode="":
    #!/usr/bin/env bash
    set -eo pipefail
    if [ -n "{{mode}}" ]; then export ORCHESTRATOR_MODE="{{mode}}"; fi
    profiles="--profile {{profile}}"
    if [ "${ORCHESTRATOR_MODE:-balancing}" != "power_saving" ]; then
      profiles="$profiles --profile {{editor_profile}}"
    fi
    mkdir -p data/postgres data/redis data/rabbitmq data/packs data/meilisearch data/clickhouse data/minio data/ollama data/grafana data/prometheus data/piston/packages
    chmod -R a+rwX data/packs 2>/dev/null || true
    {{compose}} $profiles up -d --remove-orphans

rebuild-web:
    #!/usr/bin/env bash
    set -eo pipefail
    {{compose}} --profile {{profile}} build web
    {{compose}} --profile {{profile}} up -d --force-recreate web nginx
    echo "Web image rebuilt — hard-refresh the browser (Ctrl+Shift+R)."
    echo "Tip: for UI edits use \`just web-dev\` (HMR, no production Nuxt rebuild)."

rebuild-svc +services:
    #!/usr/bin/env bash
    set -eo pipefail
    {{compose}} --profile {{profile}} build {{services}}
    {{compose}} --profile {{profile}} up -d --force-recreate {{services}}
    echo "Rebuilt: {{services}}"

web-dev:
    #!/usr/bin/env bash
    set -eo pipefail
    profiles="--profile {{profile}}"
    if [ "${ORCHESTRATOR_MODE:-balancing}" != "power_saving" ]; then
      profiles="$profiles --profile {{editor_profile}}"
    fi
    {{compose_web_dev}} $profiles up -d --build web nginx
    echo "Web HMR is up — open http://localhost (source: apps/web)"

web-local:
    #!/usr/bin/env bash
    set -eo pipefail
    cd apps/web
    if [ ! -d node_modules ]; then npm ci; fi
    echo "Open http://localhost:3000 — /api proxies to the Docker stack on :80"
    NUXT_TYPE_CHECK=false NUXT_PUBLIC_API_BASE=/api npm run dev -- --host 127.0.0.1 --port 3000

down:
    {{compose_web_dev}} --profile {{profile}} --profile {{editor_profile}} down

logs service:
    {{compose}} logs -f {{service}}

piston-install:
    #!/usr/bin/env bash
    set -eo pipefail
    {{compose}} --profile {{profile}} up -d piston
    {{compose}} --profile {{profile}} cp scripts/install_piston_packages.py grading:/tmp/install_piston_packages.py
    {{compose}} --profile {{profile}} exec -T grading python /tmp/install_piston_packages.py --url http://piston:2000

test:
    #!/usr/bin/env bash
    set -eo pipefail
    uv sync --all-packages
    unset DATABASE_URL
    shared_path="packages/python-common/src:packages/contracts:packages/integration-sdk"
    PYTHONPATH="$shared_path" uv run pytest -q \
      packages/python-common/tests \
      packages/contracts/tests
    services=(
      auth catalog media studio-api grading sessions tutor cursor-proxy
      integrations analytics lab-runner orchestrator
    )
    for svc in "${services[@]}"; do
      root="services/${svc}"
      if [ ! -d "${root}/tests" ]; then
        continue
      fi
      echo "==> pytest ${root}/tests"
      PYTHONPATH="${root}:${root}/tests:${shared_path}" uv run pytest -q "${root}/tests"
    done
    if [ -d apps/web/node_modules ]; then
      (cd apps/web && npm run test)
    fi

lint:
    uv run ruff check packages/python-common packages/contracts services scripts
    uv run ruff format --check packages/python-common packages/contracts services scripts
    uv run mypy packages/python-common/src
    bash scripts/ci/check-launcher.sh
    bash scripts/ci/check-compose.sh
    bash scripts/ci/check-tracked-modules.sh
    @if [ -d apps/web/node_modules ]; then cd apps/web && npm run lint; fi

hooks:
    uv sync --group dev
    uv run pre-commit install
    @echo "pre-commit installed — hooks run on every git commit."

hooks-run:
    uv run pre-commit run --all-files

fmt:
    uv run ruff format packages/python-common packages/contracts services scripts
    uv run ruff check --fix packages/python-common packages/contracts services scripts

validate-pack path:
    uv run python packages/contracts/validate_pack.py {{path}}

validate-schemas:
    uv run python scripts/validate_pack_schema.py

validate-integrations:
    uv run python scripts/validate_integration_fixtures.py

ci: lint validate-schemas validate-integrations test

e2e:
    #!/usr/bin/env bash
    set -eo pipefail
    export E2E_BASE_URL="${E2E_BASE_URL:-http://localhost}"
    cd apps/web
    npm run test:e2e

build-images tag="latest":
    #!/usr/bin/env bash
    set -eo pipefail
    registry="${DOCKER_REGISTRY:-ghcr.io/task-studio}"
    mkdir -p "{{buildx_cache}}"
    host_platform="linux/$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')"
    docker buildx bake -f deploy/docker-bake.hcl \
      --set "*.platform=${host_platform}" \
      --set "REGISTRY=${registry}" \
      --set "TAG={{tag}}"

publish tag="latest":
    #!/usr/bin/env bash
    set -eo pipefail
    : "${DOCKER_REGISTRY:?Set DOCKER_REGISTRY in .env}"
    mkdir -p "{{buildx_cache}}"
    docker buildx bake -f deploy/docker-bake.hcl --push \
      --set "REGISTRY=${DOCKER_REGISTRY}" \
      --set "TAG={{tag}}"
