# Course strategies (article → pack)

Strategies are **first-class harness resources** next to `roles/`, `skills/`, and `provider/`.
They apply to **every** LLM provider (Ollama, external, Cursor). Provider profiles change
tone and format-forcing only — not curriculum / theory / quiz / practice strategy IDs.

Language: **English only** (project MD rule). Learner locale (`ru` / `en`) is a runtime
request field, never the language of these files.

## Layers

| Layer | Answers | Consumed by |
| --- | --- | --- |
| **Strategy** | What must be true; forks; gates | Pipeline code + short `## LLM brief` |
| **Skill / role** | How to write text / JSON | `compose_prompt` |
| **Provider** | How to talk to this model | `provider/*.md` |
| **Policy** | Retries, tokens, volume caps | `LocalCoursePolicy` / harness policy |

## Conflict rule

1. Strategy sets **invariants and stage order** (blueprint, visual, assess, edit gates).
2. A skill **must not override** an active strategy (e.g. `expand-dense-prose` does not
   override `montage-preserve` when pack is `preserve-7b`).
3. Compose loads stage skills from code defaults, then drops pack `Skills to skip`.
   Pack `Skills to compose` documents the intended set — it must not be injected into
   every always/stage layer (that would leak quiz skills into theory prompts).
4. Provider profiles **must not** change strategy IDs.
5. Patch a skill for style; change a strategy MD for product law.
6. Known runtime stupidity (local / cloud / agent) → `failure-modes.md` (owners table),
   then pack / provider / code — do not duplicate kill-lists into stage messages.

## Packs

| Pack | When | Target quality |
| --- | --- | --- |
| `author-full` | Any capable model (3B+), external or cloud | L2–L3; same volume, adaptive request size |
| `preserve-7b` | Manual source-fidelity run only — never auto-selected | L1 → L2 |
| `blocked` | Below minimum (e.g. &lt;7B) | do not assemble |

See `packs/*.md` and `quality-levels.md`.

## Anti-patterns (forbidden)

- **`sentence-windows` as curriculum** — first-sentence / sliding windows as chapter
  titles (caused garbage TOC). Prefer `curriculum/section-blueprint`.
- **Literary rewrite-from-scratch on small models** without blueprint — use
  `montage-preserve`.
- **`llm-rubric-only` practice** as the only path when the source has an executable medium.
- **Stack lock-in** — naming a default language, cloud vendor, or product in strategy /
  role rules. Genre comes from sources + domain overlay skills.
- Putting the strategy registry under `.plan/` — this tree is the source of truth.

## Genre

Strategies are **genre-agnostic**. The same pack builds programming, humanities,
language, science, or business courses. Medium-specific craft lives in
`skills/domain-*.md`. Strategies never require Redis, Kafka, FastAPI, Python, etc.

## Failure modes

See `failure-modes.md` for local Ollama, cloud API, and IDE-agent failure catalogs
and which layer owns each fix.

## File contract

Each strategy MD:

```markdown
# strategy-id
## Status: canonical | emergency | forbidden
## Applies to: all-providers
## Pipeline: ...
## Gates: ...
## Forbidden: ...
## Skills to compose: ...
## Skills to skip: ...
## LLM brief
...
```

Pack MD lists strategy paths and skill matrices for the run.
