# Skill: code task ladder

Create practice coding tasks from easy → hard that feel like **real work**, not toy puzzles.

## Ladder

| Level | Goal |
| --- | --- |
| easy | Apply one primary idea from the article |
| medium | Combine 2–3 ideas; handle an edge case |
| hard | Realistic scenario (safety, robustness, production habit) |

## Each task must include

- `title`, short `content` brief (what to build, constraints)
- `runtime`, `runtime_version`
- `template`: starter stub with a **domain-named** top-level function (or class method task expressed as a function) and a short docstring — name it for the task (`create_user_and_get_id`, `safe_join`, …). Do **not** require a generic name like `solve`.
- `entrypoint` (optional): same name as the function in `template` when helpful
- `tests`: at least **2** cases the harness can run (see below)
- `setup` (optional): fixture helpers / stubs prepended before the learner code

## How tests are executed

The harness discovers the function from `entrypoint` or from `template`/`source` — there is **no** mandatory default name.

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
