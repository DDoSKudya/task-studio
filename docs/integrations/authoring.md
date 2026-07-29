# Integration adapter authoring

Task Studio loads course importers from `integration_modules/` at runtime. Each adapter is a folder with `integration.json`, `importer.py`, and golden fixtures for CI.

## Layout

```
integration_modules/
  my-platform/
    integration.json
    importer.py
    fixtures/
      course_<external_id>.json
```

Copy an existing adapter (`stepik`, `exercism`, …) or start from the fields below.

## integration.json

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Stable slug used in API and search (`stepik`) |
| `version` | yes | Adapter semver (`1.0.0`) |
| `display_name` | yes | Human label in UI |
| `capabilities` | yes | Feature flags (see below) |
| `auth` | no | Auth type and settings field names |
| `entrypoints` | yes | `module:callable` map |

Example:

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

### Capabilities

- `import_course` — adapter can build a normalized pack from a remote course id
- `search_catalog` — adapter exposes `search_remote`
- `requires_auth` — user must store credentials in Settings before import
- `content_types` — hints for UI badges

## importer.py entrypoints

All callables live in `importer.py`. Signatures are conventions enforced by the integrations service.

### `health() -> dict[str, object]`

Cheap readiness check. Return `{"status": "ok", "platform": "<id>"}`.

### `list_catalog(**ctx) -> list[dict[str, object]]`

Optional browse list when `list_catalog` entrypoint is set. Items: `{id, title, description?}`.

### `search_remote(*, query: str, **ctx) -> list[dict[str, object]]`

Remote search hits with the same shape as `list_catalog`.

### `import_course(*, course_id: str, **ctx) -> tuple[dict, dict]`

Returns `(pack_raw, report_raw)`:

**pack_raw** — normalized adapter payload:

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

**report_raw** — ImportReport fields: `total_items`, `imported_full`, `imported_partial`, `skipped`, `warnings`.

Mark steps with `"fidelity": "partial"` when content is lossy. The pack builder turns this into manifest v1 and runs JSON Schema validation.

## Fixtures (required for CI)

Place one JSON file per importable course:

```
fixtures/course_123.json
```

The file must contain at least `title`, `topics`, and `steps` in the shape your `import_course` expects. CI runs `scripts/validate_integration_fixtures.py` — it calls `health`, `import_course` for every fixture, and validates the built manifest.

No network calls in fixtures mode: read from `fixtures/course_{id}.json` like the built-in adapters.

## Local validation

```bash
just validate-integrations
```

## Runtime reload

Adapters are discovered on integrations service startup from the mounted `integration_modules` volume. After adding a folder, restart the integrations container or call the internal reload endpoint when a system token is configured.

## Checklist

1. Unique `id` in `integration.json`
2. All entrypoints resolve to callables in `importer.py`
3. At least one `fixtures/course_*.json`
4. `just validate-integrations` passes
5. Optional: live import tested manually via Search → Import in the web UI
