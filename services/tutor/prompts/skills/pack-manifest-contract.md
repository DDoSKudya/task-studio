# Skill: pack manifest contract

Final assembled pack must be Task Studio manifest schema v1:

- `schema_version`: 1
- `id`, `version`, `title`, `locale`
- `source`: `{ "type": "local" }`
- `defaults.runtime` / `defaults.runtime_version` when code steps exist
- `policies` with skip_study_allowed, assess settings
- `topics[]` with nested phases:
  - `"study": { "steps": ["theory-..."] }`
  - `"practice": { "steps": ["code-..."] }`
  - `"assess": { "steps": ["quiz-..."] }`
- `steps` map: id → step object (`kind`, `title`, …)

Ids: lowercase snake_case / kebab-safe (`[a-z0-9-]+`).
Video steps (`kind: video` + `video_url`) only when the article HTML/markdown supplies
a real external player URL (YouTube/Vimeo/direct). Do not invent videos. Place them as
**separate study slides** (not inside theory markdown). Lab: omit in v1.

Theory may embed at most 1–2 source figures as markdown `![alt](https://…)` copied from
the article — never invent image URLs.
