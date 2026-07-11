set dotenv-load := true

compose := "docker compose -f deploy/docker-compose.yml --env-file .env"
profile := "full"

default:
    @just --list

up:
    {{compose}} --profile {{profile}} up -d --build

down:
    {{compose}} --profile {{profile}} down

logs service:
    {{compose}} logs -f {{service}}

test:
    uv sync --all-packages
    uv run pytest -q
    @if [ -d apps/web/node_modules ]; then cd apps/web && npm run test; fi

lint:
    uv run ruff check packages/python-common packages/contracts services
    uv run ruff format --check packages/python-common packages/contracts services
    uv run mypy packages/python-common/src
    @if [ -d apps/web/node_modules ]; then cd apps/web && npm run lint; fi

fmt:
    uv run ruff format packages/python-common packages/contracts services
    uv run ruff check --fix packages/python-common packages/contracts services

validate-pack path:
    uv run python packages/contracts/validate_pack.py {{path}}

build-images:
    @echo "Multi-arch image build is not configured yet"

publish:
    @echo "Configure registry in deploy/docker-bake.hcl before publish"
