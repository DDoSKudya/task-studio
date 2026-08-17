# harvest-then-drill

## Status: canonical
## Applies to: all-providers
## Pack: preserve-7b (primary)

## Pipeline

1. Prefer harvested labs from the article.
2. Else build a completion problem from a key claim.
3. Choose runtime from the source medium: shell fences, prompts, or `<tool>-cli`
   invocations → shell; language fences → that language. Do not infer a client
   language merely from the product being taught.

## Gates

- Prefer real `tests` when the runtime is executable in the lab
- `checker=llm` alone only when no executable runtime exists
- Template must not invent nonexistent packages
- Rubric describes the observable outcome

## Forbidden

- Fake npm/pip packages not in the article
- Server-config drills forced into the wrong client runtime without reason

## Skills to compose

- `practice-as-drill`, `course-stage-json`

## Skills to skip

- `code-task-ladder` on preserve packs (one harvest drill, not a 3-rung ladder)
- `open-task-ladder` on preserve packs (same rule for non-code drills)

## LLM brief

Create one focused practice drill for this chapter claim. Match the article’s
medium and tools (code runtime, case memo, language production, numeric drill —
whatever the source teaches). Prefer a completion problem over a blank file.
JSON only. Never invent packages, datasets, or citations absent from the article.
