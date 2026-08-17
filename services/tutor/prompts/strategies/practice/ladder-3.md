# ladder-3

## Status: canonical
## Applies to: all-providers
## Pack: author-full

## Pipeline

Emit easy → medium → hard code tasks with templates and automated tests when the
lab runtime supports them.

## Gates

- Three distinct difficulties when practice is ON and volume allows
- Tests present for piston/lab runtimes whenever feasible
- Same anti-fake-package rules as harvest-then-drill

## Forbidden

- Three identical stubs with different titles

## Skills to compose

- `code-task-ladder`, `practice-as-drill`, `course-stage-json`

## Skills to skip

- none

## LLM brief

Build an easy→medium→hard practice ladder grounded in the chapter excerpt.
Templates and tests must be runnable. JSON only.
