set dotenv-load := true

compose := "docker compose -f deploy/docker-compose.yml --env-file .env"
profile := "full"
editor_profile := "editor"

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
    {{compose}} $profiles up -d --build

down:
    {{compose}} --profile {{profile}} --profile {{editor_profile}} down

logs service:
    {{compose}} logs -f {{service}}

test:
    uv sync --all-packages
    uv run pytest -q
    @if [ -d apps/web/node_modules ]; then cd apps/web && npm run test; fi

lint:
    uv run ruff check packages/python-common packages/contracts services scripts
    uv run ruff format --check packages/python-common packages/contracts services scripts
    uv run mypy packages/python-common/src
    @if [ -d apps/web/node_modules ]; then cd apps/web && npm run lint; fi

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

build-images tag="latest":
    #!/usr/bin/env bash
    set -eo pipefail
    registry="${DOCKER_REGISTRY:-ghcr.io/task-studio}"
    docker buildx bake -f deploy/docker-bake.hcl --set REGISTRY="${registry}" --set TAG="{{tag}}"

publish tag="latest":
    #!/usr/bin/env bash
    set -eo pipefail
    : "${DOCKER_REGISTRY:?Set DOCKER_REGISTRY in .env}"
    docker buildx bake -f deploy/docker-bake.hcl --push --set REGISTRY="${DOCKER_REGISTRY}" --set TAG="{{tag}}"
