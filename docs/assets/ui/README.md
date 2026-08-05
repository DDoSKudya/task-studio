# Снимки интерфейса для документации

Файлы PNG ниже используются в [`DEVELOPERS.md`](../../DEVELOPERS.md). Они сняты с **живого** интерфейса Nuxt/Vue на поднятом стеке (`http://localhost`), а не с макета PREVIEW.

Перед сохранением `scripts/docs-capture-ui.py` маскирует:

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

## Как переснять

```bash
# из корня репозитория, стек на http://localhost
DOCS_UI_EMAIL='…' DOCS_UI_PASSWORD='…' python scripts/docs-capture-ui.py
```

Не коммитьте PNG с заполненными паролями, токенами, Client Secret или реальной почтой/названиями курсов учётки. После съёмки имеет смысл быстро проверить:

```bash
rg -a 'igor@|kud93|Client Secret' docs/assets/ui || true
```

Макет README: [`../readme-preview.png`](../readme-preview.png) из [`../../PREVIEW.md`](../../PREVIEW.md).
