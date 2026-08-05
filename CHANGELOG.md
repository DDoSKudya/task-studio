# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-release and build rules described in [docs/VERSIONING.md](docs/VERSIONING.md).

## [1.1.0-beta.1] - 2026-08-05

**Build:** `101002001`  
**Channel:** `beta`  

Large minor pre-release after `1.0.0-alpha`: redesigned learning/catalog UI, stronger local AI (Ollama), launcher and deploy profiles, article→course generation with checkpoints and multi-URL paste, Stepik / freeCodeCamp / Exercism integrations, cascading grading, security hardening, and a large remediation bug-fix cycle.

### Added

#### Launcher and install
- Deploy profiles (`deploy/profiles.json`) and launcher matrix (`scripts/launcher-matrix.json`) as the single source of truth for env keys and stack composition.
- Launcher product identity via `scripts/launcher-version.json` (`1.0.0-beta.1` / build `100002001`), shown in TUI title and footer (bash + PowerShell).
- Free HTTP port selection on Windows/Linux when the default port is taken; clear diagnostics for `TASK_STUDIO_HTTP_PORT` conflicts.
- Reworked launcher menu copy (short titles, readable descriptions, first-install vs rebuild messaging).
- Improved Docker Desktop / daemon wait; `Health` / `Profiles` / `Ops` / `Ui` / `I18n` helpers (bash + PowerShell).
- Launcher bootstrap smoke checks and compose / tracked-file CI checks.

#### Ollama and local AI
- GPU profile for Ollama (`deploy/docker-compose.ollama-gpu.yml`): GPU when available, otherwise CPU.
- Pinned Ollama / Piston images in compose and `.env.example`.
- Live Ollama model list in Settings UI (dropdown + e2e coverage).
- LLM task routing (chat / hints / grade / course build) with distinct `num_ctx` and contours A–D.
- Ollama response polish, weak-machine guards, and cautious mode for free cloud keys (e.g. Mistral).
- Modular tutor prompts: roles, skills, provider profiles; current course-page context and in-session chat history.

#### Cursor and cloud agents
- OpenAI-compatible `cursor-proxy` (agents, SSE, keepalive, warm-up).
- Unified Settings providers screen: local agent / cloud agent / Cursor SDK with aligned RU/EN labels.

#### Article → local course (AI author)
- On-disk build checkpoints (`COURSE_BUILDS_ROOT`), TTL, `course-builds` API, resume by `build_id`.
- Incomplete builds in My library with Resume and a counter badge.
- Course scale: theory / questions / tasks (limits up to 100), dynamic practice difficulty, defaults 20 / 12 / 2.
- Multi-URL paste (newline, comma, `;`, `|`); sequential fetch queue with progress; `fetch-articles-from-urls` API.
- Article image harvest into theory (allowlisted) and separate video steps; Mermaid wheel zoom / double-click reset.
- Harvest of exercise/quiz/lab blocks from article text → seeds for assess/practice; instructional-design (Merrill micro-cycle, learning objectives).
- Partial builds on 429 / quota exhaustion with clear UI warnings.
- Localized course-build progress strings (RU/EN).

#### Learning and grading
- Cascade grading: Stepik API → Piston / local SQL → LLM fallback; correct/incorrect answer highlighting.
- Progress gates (cannot advance until quiz/code passed); unique active session per course.
- Lab-runner system token on complete/callback; honest fail when `LAB_RUNNER_DRY_RUN` is set.
- Analytics event outbox + background flush; resilient ingest when ClickHouse fails.

#### Catalog and integrations
- Stepik / freeCodeCamp / Exercism import and display without empty shells; step phases/types, quiz options, code zones.
- Source filters in catalog and My library (local / external / by platform).
- Composition labels: theory, questions, tasks, video (RU short labels when locale is Russian).

#### UI / UX
- Unified violet–gold palette (op-skin), page and button transitions.
- Session page: theory markup (tables, code, HTML sanitize + DOMPurify), video player, step navigation, docked code editor.
- Toasts instead of scattered status chips; browser tab titles (`useAppPageTitle`).
- AI-author modal: sources rail up to 50 slots, taller sources layout, fixed URL field (no resize), no outer form scroll.

#### Security, license, infrastructure
- AGPL-3.0 + `LICENSE-SUPPLEMENT.md` (no monetization / white-label of official distributions without a separate agreement).
- Log redaction (`log_redact`), MinIO presign TTL clamp, catalog without root `user:0:0`, JWT rotate / `COOKIE_SECURE` when UI is HTTPS.
- System auth for inter-service complete; basedpyright in CI lint; search tests in `just test`.
- ADR: stay on Nuxt 3; Helm / nginx / Traefik updates for the current stack.

### Changed

- Catalog and course cards: compact icon actions; shared visual language for Find courses / My library.
- AI settings: merged external OpenAI-compatible providers; agent-oriented copy.
- `just up` rebuilds images and starts the stack in one command; Docker layer caching improvements (~50% faster typical rebuilds as a target).
- Course generation: larger corpus budgets (head+mid+tail), teaching-only corpus, harvested seeds instead of generic filler.
- Heal broken markdown fences (backend assemble + frontend sanitize) for Python blocks.
- Pack delete: parallel media delete (semaphore) and related resource cleanup.
- Sessions: indexes, unique active session, attempts; list without heavy `manifest` (defer + limit).
- Orchestrator: generation load-balancing policies / grading-hot probes.
- Stepik/FCC/Exercism importers: strict typing without `Any`, robust JSON parsing.

### Fixed

- Session start, duplicate courses on home, search, UI vanishing when switching AI providers.
- Video / quiz / code steps mislabeled as theory; truncated or flat step text.
- Course delete and home progress sync; 500 on pack delete.
- Code and SQL grading (`solve_sql` schema, local fallback / emulation).
- Ollama 500 / timeouts / “unavailable”; tutor chat and hints button.
- Library ↔ catalog transition animations (source filter width no longer jumps mid-transition).
- Service ready probes: unavailable DB returns **503 degraded**, not 500.
- Many remediation audit items (W0–W9, MED/LOW errors/security/typing): smoke, local CI, outbox, lab complete jail without token, and more.

### Removed

- Moodle and OLX integrations (unsupported API surfaces).
- Client Vidstack plugin (session player path updated).
- Duplicate “Upload pack” button and redundant catalog status chips.

### Security

- XSS: final DOMPurify pass in `sanitizeStudyHtml`.
- Secrets redacted from logs; MinIO object keys scoped under the user namespace.
- Inter-service callbacks require a system token.

### Documentation

- Updated `docs/DEVELOPERS.md`, remediation pack (problem catalog, roadmap, MED/LOW status).
- Extended `.env.example`, compose profiles, `runtime_modules` README.
- Added `docs/VERSIONING.md` (SemVer channels + integer build formula).

---

## [1.0.0-alpha.1] - 2026-07-29

**Build:** `100001001`  
**Channel:** `alpha`  

### Added
- **Core platform**: Unified intake pipeline (structured text form & guided AI chat), weekly Kanban board with drag-and-drop, and background jobs UI.
- **AI & tutoring**: Full AI integration (Ollama, OpenAI, Mistral, Grok, Cursor SDK) featuring guided checklists, automatic preview modals, voice input, and vision capabilities.
- **Content & integrations**: Course generation from web articles or `.md` files; import from external platforms (Stepik, freeCodeCamp, Exercism).
- **Code editor**: Monaco-based environment with 90+ syntax highlighting and smart autocomplete for Python, SQL, JavaScript, and Go.
- **Analytics & exports**: Detailed progress tracking, Grafana/Prometheus observability.
- **Infrastructure**: Modular monolith backend (FastAPI, PostgreSQL 16, Redis, RabbitMQ, MinIO, Meilisearch, ClickHouse) and modern frontend (Nuxt 3, Vue 3, TypeScript, Tailwind).
- **Deployment**: One-click cross-platform installation scripts (`install.sh`, `install.ps1`) and Docker Compose stack with nginx/Traefik edge routing.
- **Security & CI**: AES-GCM encryption for local integration credentials, comprehensive CI/CD pipeline, pre-commit hooks, and 157+ automated tests (backend + frontend).
- **Documentation**: Complete developer guide (`DEVELOPERS.md`) and fully localized interface (RU/EN).

[1.1.0-beta.1]: https://github.com/DDoSKudya/task-studio/releases/tag/v1.1.0-beta.1
[1.0.0-alpha.1]: https://github.com/DDoSKudya/task-studio/releases/tag/v1.0.0-alpha.1
