# Task Studio — руководство разработчика

Краткая продуктовая инструкция — в [README.md](../README.md). Здесь: стек, структура, локальная разработка, публикация образов.

## Стек

| Слой | Технологии |
|---|---|
| UI | Nuxt 3, Vue 3, TypeScript (`apps/web`, `apps/pack-studio`) |
| BFF | FastAPI `studio-api` |
| Домен | FastAPI-сервисы: auth, catalog, sessions, grading, integrations, tutor, search, analytics, media, lab-runner, orchestrator, cursor-proxy |
| Данные | PostgreSQL, Redis, RabbitMQ, MinIO, Meilisearch, ClickHouse |
| ИИ | Ollama (+ опционально внешние OpenAI-совместимые провайдеры и Cursor через `cursor-proxy`) |
| Edge | nginx, Traefik |
| Качество | ruff, basedpyright/mypy, pytest, vitest, Playwright |
| Сборка | Docker Buildx, `uv`, npm |

## Структура репозитория

| Путь | Назначение |
|---|---|
| `services/*` | Микросервисы FastAPI |
| `apps/web` | UI обучающегося |
| `apps/pack-studio` | UI автора пакетов |
| `packages/python-common` | Общие Python-утилиты |
| `packages/contracts` | Pydantic-схемы и JSON Schema пакета |
| `packages/editor-core` | Редактор / LSP-клиент |
| `integration_modules/` | Импортёры курсов |
| `runtime_modules/` | Рантаймы исполнения кода |
| `deploy/` | Compose, nginx, Grafana, bake |
| `scripts/` | Установка, остановка, утилиты |
| `docs/` | Документация |

## Установка одной командой

См. [README.md](../README.md). Скрипты:

- `scripts/install.sh` / `scripts/install.ps1` — клон (при необходимости), `.env`, `compose build/up`, ожидание UI, `ollama pull`
- `scripts/stop.sh` / `scripts/stop.ps1` — остановка стека

Переменные окружения установщика (опционально):

| Переменная | По умолчанию |
|---|---|
| `TASK_STUDIO_DIR` | `$HOME/task-studio` |
| `TASK_STUDIO_BRANCH` | `develop` |
| `TASK_STUDIO_MIN_RAM_GB` | `8` |
| `OLLAMA_MODEL` | `qwen2.5:3b` |
| `ORCHESTRATOR_MODE` | авто: `power_saving` при RAM &lt; 16 ГБ, иначе `balancing` |

## Разработка на уже склонированном репо

Нужны Docker, при желании [mise](https://mise.jdx.dev/), [just](https://github.com/casey/just), [uv](https://docs.astral.sh/uv/), Node 22+.

```bash
cp .env.example .env
# SECRETS_MASTER_KEY должен декодироваться из Base64 ровно в 32 байта
# JWT_SECRET — длинная случайная строка
./scripts/install.sh
# или:
just up
```

Полезные команды `just`:

| Команда | Действие |
|---|---|
| `just up` | Полная пересборка + старт |
| `just start` | Старт без пересборки |
| `just down` | Остановка |
| `just rebuild-svc <name…>` | Пересборка отдельных сервисов |
| `just web-dev` | Nuxt HMR в Docker |
| `just test` / `just lint` / `just ci` | Проверки |

Оболочка разработчика (mise + just в shell):

```bash
chmod +x scripts/setup-shell.sh && ./scripts/setup-shell.sh
```

### Frontend hot reload

Не гоняйте `just up` на каждое изменение UI.

```bash
just start
just web-dev          # http://localhost
# или
just web-local        # http://localhost:3000, API через Docker
```

## Compose и профили

Файл: `deploy/docker-compose.yml`.

| Профиль | Содержание |
|---|---|
| `full` | Ядро платформы + данные + tutor/ollama + observability |
| `editor` | LSP (pyright, typescript, gopls, sqls) |

Данные на хосте: каталог `data/` (в `.gitignore`). Конфиги edge: `deploy/nginx`, `deploy/traefik`, …

Сервисы `orchestrator`, `lab-runner`, Traefik монтируют `/var/run/docker.sock`.
Piston запускается с `privileged: true`.

## Секреты и `.env`

| Переменная | Требование |
|---|---|
| `SECRETS_MASTER_KEY` | Base64 → ровно 32 байта |
| `JWT_SECRET` | Непредсказуемая строка |
| `COOKIE_SECURE` | `true` только за HTTPS |
| `DOCKER_GID` | GID группы `docker` на Linux (скрипт выставляет сам) |

Локальные учётные данные интеграций хранятся в БД в зашифрованном виде (AES-GCM).

## Публикация образов

```bash
# в .env: DOCKER_REGISTRY, DOCKER_USERNAME, DOCKER_PASSWORD
just build-images
just publish tag=v0.1.0
```

Bake: `deploy/docker-bake.hcl` (linux/amd64 + linux/arm64).
CI: `.github/workflows/publish-images.yml` на теги `v*`.

Когда образы опубликованы, установщик можно перевести на `pull`-only compose (отдельный файл с `image:` без `build:`) — см. bake-имена `task-studio-*`.

## Мониторинг

| Сервис | Адрес |
|---|---|
| Сайт | http://localhost |
| Grafana (дашборды) | http://localhost:3001 |
| Prometheus (метрики) | http://localhost:9090 |

## Тесты

```bash
just test
just e2e   # стек должен быть запущен; один раз: cd apps/web && npx playwright install chromium
```

## Безопасность self-hosted

- Не публикуйте `.env`, ключи, содержимое `data/`.
- Ограничьте доступ к Docker socket на хосте.
- За reverse-proxy включите TLS и `COOKIE_SECURE=true`.
