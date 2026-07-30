# Написание адаптера интеграции

Task Studio подгружает импортёры курсов из `integration_modules/` во время работы. Каждый адаптер — папка с `integration.json`, `importer.py` и golden-фикстурами для CI.

## Структура

```
integration_modules/
  my-platform/
    integration.json
    importer.py
    fixtures/
      course_<external_id>.json
```

Скопируйте существующий адаптер (`stepik`, `exercism`, …) или соберите по полям ниже.

## integration.json

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `id` | да | Стабильный slug в API и поиске (`stepik`) |
| `version` | да | Semver адаптера (`1.0.0`) |
| `display_name` | да | Подпись в интерфейсе |
| `capabilities` | да | Флаги возможностей (см. ниже) |
| `auth` | нет | Тип аутентификации и имена полей настроек |
| `entrypoints` | да | Карта `module:callable` |

Пример:

```json
{
  "id": "stepik",
  "version": "1.1.0",
  "display_name": "Stepik",
  "capabilities": {
    "import_course": true,
    "search_catalog": true,
    "requires_auth": true,
    "content_types": ["quiz", "code", "theory", "video"]
  },
  "auth": { "type": "password", "settings_fields": ["username", "password"] },
  "entrypoints": {
    "health": "importer:health",
    "import": "importer:import_course",
    "search": "importer:search_remote",
    "list_catalog": "importer:list_catalog"
  }
}
```

### Возможности (capabilities)

- `import_course` — адаптер собирает нормализованный пакет по id удалённого курса
- `search_catalog` — есть `search_remote`
- `requires_auth` — перед импортом пользователь сохраняет учётные данные в настройках
- `content_types` — подсказки для бейджей в UI

## Точки входа importer.py

Все вызываемые функции живут в `importer.py`. Сигнатуры — соглашения, которые проверяет сервис integrations.

### `health() -> dict[str, object]`

Лёгкая проверка готовности. Верните `{"status": "ok", "platform": "<id>"}`.

### `list_catalog(**ctx) -> list[dict[str, object]]`

Необязательный список для обзора, если задан entrypoint `list_catalog`. Элементы: `{id, title, description?}`.

### `search_remote(*, query: str, **ctx) -> list[dict[str, object]]`

Результаты удалённого поиска в том же виде, что и `list_catalog`.

### `import_course(*, course_id: str, **ctx) -> tuple[dict, dict]`

Возвращает `(pack_raw, report_raw)`:

**pack_raw** — нормализованная нагрузка адаптера:

```python
{
    "platform": "stepik",
    "external_id": "123",
    "title": "Intro Python",
    "slug": "stepik-123",
    "version": "1.0.0",
    "locale": "en",
    "topics": [...],
    "steps": {...},
    "course_assess": [],
}
```

**report_raw** — поля ImportReport: `total_items`, `imported_full`, `imported_partial`, `skipped`, `warnings`.

Помечайте шаги `"fidelity": "partial"`, если контент потерян частично. Сборщик пакета превращает это в manifest v1 и прогоняет JSON Schema.

## Фикстуры (обязательны для CI)

Один JSON-файл на импортируемый курс:

```
fixtures/course_123.json
```

В файле как минимум `title`, `topics` и `steps` в том виде, который ждёт ваш `import_course`. CI запускает `scripts/validate_integration_fixtures.py` — вызывает `health`, `import_course` для каждой фикстуры и проверяет собранный манифест.

В режиме фикстур без сети: читайте `fixtures/course_{id}.json`, как встроенные адаптеры.

## Локальная проверка

```bash
just validate-integrations
```

## Перезагрузка в рантайме

Адаптеры находятся при старте сервиса integrations из смонтированного тома `integration_modules`. После добавления папки перезапустите контейнер integrations или вызовите внутренний reload, если настроен системный токен.

## Чеклист

1. Уникальный `id` в `integration.json`
2. Все entrypoints указывают на вызываемые объекты в `importer.py`
3. Хотя бы один `fixtures/course_*.json`
4. `just validate-integrations` проходит
5. По желанию: живой импорт вручную через «Поиск → Импорт» в веб-UI
