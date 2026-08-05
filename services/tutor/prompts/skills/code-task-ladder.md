# Skill: code task ladder

Create practice coding tasks from easy → hard that feel like **real work**, not toy puzzles.

## Alignment

- Each task must exercise skills from the **course arc** — easy maps to an early chapter
  objective, hard combines several.
- Brief in `content` should reference the scenario from theory (same vocabulary / mental model).
- **Fading:** easy template may include more stub/scaffolding; hard template leaves more for
  the learner to implement (fewer hints, stricter constraints).

## Ladder

| Level | Goal |
| --- | --- |
| easy | Apply one primary idea from the article |
| medium | Combine 2–3 ideas; handle an edge case |
| hard | Realistic scenario (safety, robustness, production habit) |

## Each task must include

- `title`
- `content`: learner-facing brief in markdown (not a one-liner). Prefer this shape:
  1. **What to build** — 1–2 sentences
  2. **Input** — arguments / types / example values the function receives
  3. **Output** — return shape with field names and meaning
  4. **Constraints** — allowed libs, edge cases, what not to do
  Keep secrets out of `content` (no hidden expected answers for graded tests).
- `runtime`, `runtime_version`
- `template`: starter stub with a **domain-named** top-level function (or class method task expressed as a function) and a short docstring — name it for the task (`create_user_and_get_id`, `safe_join`, …). Do **not** require a generic name like `solve`. Docstring may repeat I/O briefly; the full contract lives in `content`.
- `entrypoint` (optional): same name as the function in `template` when helpful
- `tests`: at least **2** cases the harness can run (see below)
- `setup` (optional): fixture helpers / stubs prepended before the learner code

## How tests are executed

The harness discovers the function from `entrypoint` or from `template`/`source` — there is **no** mandatory default name.

When the harness provides **harvested article labs**, adapt those first into clear ТЗ
(Input / Output / Constraints) before inventing unrelated exercises.

Prefer pure JSON I/O when possible:

```json
{ "input": [2, 3], "output": 5 }
```

→ calls `entrypoint(*input)` and compares to `output`.

When the task needs objects (session, fake FS, callbacks), do **not** pass fake strings like `"mock_session"`. Instead:

1. Put stubs in `setup` (e.g. `User`, `MockSession`, `make_session`).
2. Either use fixture calls in inputs: `{ "input": [{"$call": "make_session"}, "a@b.c"], "output": 1 }`
3. Or use scripted cases: `{ "run": "s = make_session()\\nassert create_user_and_get_id(s, 'a@b.c') == 1" }`

## Quality

- Inputs/outputs / `run` scripts must match the template signature and story in `content`.
- Prefer pure functions (no network, no real filesystem writes) unless the article is about FS and you use tempfile-safe patterns via returned values.
- If the task needs objects/mocks that cannot be expressed as JSON + `setup`, set `"checker": "llm"` and a clear `"rubric"` instead of fake `"mock_session"` strings.
- Difficulty must visibly increase across the three tasks.
- Do not require libraries not implied by the article; if the article uses an ORM, emulate it with light stubs in `setup`, not with uninstalled packages.
- **CLI / DevOps / Docker / shell-first labs:** do not emit Python/JS functions that *return* a Dockerfile or shell script as a string. Those steps belong in `kind: task` (learner pastes Dockerfile or commands) or use `runtime: bash` with a real script template — never `def create_dockerfile(...) -> str`.
- Do not paste sample `requirements.txt`, `package.json`, or dependency manifests into learner `content` — the platform provisions dependencies at check time when needed.
