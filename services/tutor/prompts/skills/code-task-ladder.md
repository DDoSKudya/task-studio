# Skill: code task ladder

Only when this run includes practice. Coding drills easy → hard that feel like
**real work**, not toy puzzles. If practice is OFF, do not emit tasks.

## Alignment

- Every task drills **this chapter's** objective (same skill, fading scaffold).
- Hard must **not** invent tools from later chapters.
- Prefer **harvested article labs** first, then invent only if needed.
- Prefer a **completion problem**: copy the worked example, delete 2–4 decisive
  lines, leave `# TODO` — do not invent a new API.

## Ladder

| Level | Goal |
| --- | --- |
| easy | Finish the chapter worked example with heavy scaffold |
| medium | Same skill; less scaffold; one edge from this chapter |
| hard | Same skill as a short authentic product (still no new APIs) |

## Required fields

- `title`, `content` (1–2 sentences: what to finish; no hidden answers)
- `runtime`, `runtime_version`
- `template`: domain-named function (not `solve`); short docstring OK
- `entrypoint` optional; match the template function name
- `tests`: ≥2 runnable cases when possible; else `"checker": "llm"` + `"rubric"`
- `setup` optional for fixtures/stubs

## Tests (short)

Prefer `{ "input": [...], "output": ... }` calling `entrypoint(*input)`.
For objects: stubs in `setup` + `$call` / `run` — never fake `"mock_session"` strings.
Do not paste `requirements.txt` / `package.json` into `content`.

## Forbidden

- Olympiad novelty / new APIs absent from theory
- Three tasks that only rename variables
- Python/JS that *returns* a Dockerfile or shell script as a string — use
  `kind: task` or `runtime: bash` instead (see domain-programming)
