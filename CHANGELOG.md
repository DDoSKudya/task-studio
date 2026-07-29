# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-29

### Added
- **Core Platform**: Unified intake pipeline (structured text form & guided AI chat), weekly Kanban board with drag-and-drop, and background jobs UI.
- **AI & Tutoring**: Full AI integration (Ollama, OpenAI, Mistral, Grok, Cursor SDK) featuring guided checklists, automatic preview modals, voice input, and vision capabilities.
- **Content & Integrations**: Course generation from web articles or `.md` files; seamless import from external platforms (Stepik, freeCodeCamp, Exercism).
- **Code Editor**: Monaco-based environment with 90+ syntax highlighting and smart autocomplete for Python, SQL, JavaScript, and Go.
- **Analytics & Exports**: Detailed progress tracking, Grafana/Prometheus observability.
- **Infrastructure**: Modular monolith backend (FastAPI, PostgreSQL 16, Redis, RabbitMQ, MinIO, Meilisearch, ClickHouse) and modern frontend (Nuxt 3, Vue 3, TypeScript, Tailwind).
- **Deployment**: One-click cross-platform installation scripts (`install.sh`, `install.ps1`) and Docker Compose stack with nginx/Traefik edge routing.
- **Security & CI**: AES-GCM encryption for local integration credentials, comprehensive CI/CD pipeline, pre-commit hooks, and 157+ automated tests (backend + frontend).
- **Documentation**: Complete developer guide (`DEVELOPERS.md`) and fully localized interface (RU/EN).