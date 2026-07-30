# Переменные окружения

Источник шаблона: [`.env.example`](../.env.example). Локальный `.env` создаётся установщиком или копированием шаблона; **не коммитьте** `.env` и содержимое `data/`.

Краткие требования к секретам также в [DEVELOPERS.md](DEVELOPERS.md).

## Обязательные для локального запуска

| Переменная | Назначение |
|---|---|
| `SECRETS_MASTER_KEY` | Base64 → ровно 32 байта. Шифрование учётных данных интеграций (AES-GCM). Заполняет `install` |
| `JWT_SECRET` | Секрет подписи JWT. Длинная случайная строка. Заполняет `install` |
| `DATABASE_URL` | PostgreSQL (asyncpg), по умолчанию сервис `postgres` |
| `REDIS_URL` | Redis |
| `RABBITMQ_URL` | RabbitMQ |

## Безопасность и cookies

| Переменная | По умолчанию | Заметка |
|---|---|---|
| `COOKIE_SECURE` | `false` | `true` только за HTTPS |
| `JWT_EXPIRE_HOURS` | `168` | Срок жизни токена |

## Сервисы (внутренние URL в Compose)

Имена хостов совпадают с сервисами в `deploy/docker-compose.yml`: `auth`, `catalog`, `sessions`, `grading`, `integrations`, `tutor`, `search`, `analytics`, `media`, `orchestrator`, `cursor-proxy` и т.д.

Примеры: `AUTH_SERVICE_URL=http://auth:8001`, `TUTOR_SERVICE_URL=http://tutor:8006`.

## ИИ / Tutor

| Переменная | Назначение |
|---|---|
| `OLLAMA_URL` | Базовый URL Ollama в сети Compose |
| `OLLAMA_MODEL` | Модель по умолчанию (для русского удобны `qwen2.5:3b` / `qwen2.5:7b`) |
| `TUTOR_DEFAULT_PROVIDER_URL` | Пусто = Ollama; иначе OpenAI-совместимый base URL |
| `TUTOR_RATE_LIMIT_PER_MINUTE` | Лимит запросов к tutor |
| `LLM_GRADE_ENABLED` | Запасная оценка через LLM, если нет локальных тестов / API |
| `LLM_GRADE_MIN_CONFIDENCE` | Минимальная уверенность для LLM-grade |
| `CURSOR_API_BASE` / `CURSOR_PROXY_*` | Адаптер Cursor через `cursor-proxy` |

## Интеграции

| Переменная | Назначение |
|---|---|
| `STEPIK_CLIENT_ID` / `STEPIK_CLIENT_SECRET` | Опционально: OAuth-приложение Stepik на всё развёртывание. Ученик в настройках вводит свой логин/пароль Stepik, не эти ключи |
| `INTEGRATIONS_SERVICE_URL` | URL сервиса интеграций |

## Хранилище и поиск

| Переменная | Назначение |
|---|---|
| `MINIO_*` | S3-совместимое хранилище медиа |
| `MEILISEARCH_URL` / `MEILISEARCH_KEY` | Поиск |
| `CLICKHOUSE_*` | Аналитика |
| `ANALYTICS_EVENTS_QUEUE` | Очередь событий аналитики |

## Оркестрация и лаборатории

| Переменная | Назначение |
|---|---|
| `ORCHESTRATOR_MODE` | `balancing` / `power_saving` (установщик может выставить по RAM) |
| `DOCKER_GID` | GID группы `docker` на Linux (нужен socket) |
| `LAB_RUNNER_DRY_RUN` | Режим без реального запуска контейнеров lab |
| `LAB_DEFAULT_TIMEOUT_SECONDS` | Таймаут lab |
| `PISTON_URL` | Исполнение кода (Piston) |

## Публикация образов (CI)

| Переменная | Назначение |
|---|---|
| `DOCKER_REGISTRY` | Реестр (например `ghcr.io/…`) |
| `DOCKER_USERNAME` / `DOCKER_PASSWORD` | Учётные данные публикации |

Не используются обычным локальным `compose up`.

## Установщик / консоль `studio`

Опциональные переменные процесса установки и самообновления — в [DEVELOPERS.md](DEVELOPERS.md) (`TASK_STUDIO_DIR`, `TASK_STUDIO_BRANCH`, `TASK_STUDIO_UPDATE_TTL_SEC`, …).
