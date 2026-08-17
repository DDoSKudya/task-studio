# Снимки интерфейса для документации

Каталог хранит снимки для [`DEVELOPERS.md`](../../DEVELOPERS.md). Они сняты с **живого** интерфейса Nuxt/Vue и консоли запуска на поднятом стеке (`http://localhost`), а не с макета PREVIEW. PNG собирает автоматическая проходка; WebP сохраняют актуальные русские экраны.

Перед сохранением `scripts/docs/capture-ui.py` маскирует:

- почту и инициалы в сайдбаре (`docs@example.com`, аватар `XX`);
- поля password / secret / token / client id / key;
- пользовательские названия курсов и тем (`Example course …`, `Example step …`, `TOPIC: EXAMPLE-…`).

| Файл                           | Экран / действие                   |
| ------------------------------ | ---------------------------------- |
| `01-login.png`                 | Вход                               |
| `02-register.png`              | Регистрация                        |
| `11-catalog.png`               | Библиотека курсов                  |
| `12-catalog-find.png`          | Поиск внешних курсов               |
| `12b-catalog-create.png`       | Форма «создать из статей»          |
| `13-analytics.png`             | Аналитика                          |
| `14-settings.png`              | Настройки (обзор)                  |
| `14b-settings-ai.png`          | Параметры ИИ-агента                |
| `14c-settings-editor.png`      | Параметры редактора                |
| `14d-settings-integration.png` | Форма интеграции (секреты очищены) |
| `15-catalog-detail.png`        | Карточка курса                     |
| `16-session.png`               | Занятие / сессия                   |
| `16b-session-actions.png`      | Кнопки навигации на шаге           |
| `20-pack-studio.png`           | Редактор Pack Studio               |
| `20b-pack-studio-actions.png`  | Validate / Build / Upload          |
| `21-pack-studio-login.png`     | Вход в Pack Studio                 |
| `11-catalog-library.webp`      | Библиотека курсов                  |
| `12-catalog-find.webp`         | Поиск внешних курсов               |
| `12c-catalog-create-sources.webp` | Добавление источников статьи    |
| `12d-catalog-create-options.webp` | Состав и глубина курса          |
| `12e-catalog-build-progress.webp` | Прогресс сборки курса           |
| `13-analytics.webp`            | Аналитика                          |
| `14-settings.webp`             | Настройки интеграций и ИИ          |
| `15-catalog-detail.webp`       | Карточка и программа курса         |
| `16-session-theory.webp`       | Теоретический шаг                  |
| `16c-session-quiz.webp`        | Вопрос с вариантами                |
| `16d-session-code.webp`        | Практика в редакторе               |
| `30-launcher-running.webp`     | Запущенный стек в консоли          |

## Как переснять

```bash
# из корня репозитория, стек на http://localhost
DOCS_UI_EMAIL='…' DOCS_UI_PASSWORD='…' python scripts/docs/capture-ui.py
```

Не коммитьте снимки с заполненными паролями, токенами, Client Secret или реальной почтой. После съёмки имеет смысл быстро проверить:

```bash
rg -a 'igor@|kud93|Client Secret' docs/assets/ui || true
```

Макет README: [`../readme-preview.png`](../readme-preview.png) из [`../../PREVIEW.md`](../../PREVIEW.md) — переснять: `python scripts/docs/capture-preview.py`.
