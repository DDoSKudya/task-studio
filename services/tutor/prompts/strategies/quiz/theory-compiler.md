# theory-compiler

## Status: emergency
## Applies to: all-providers

## Pipeline

If LLM quiz JSON fails once for a chapter, compile a single fallback MCQ from
theory claims. At most **one** compiler item per chapter. Prefer failing L3 warn
over flooding the pack with templates.

## Gates

Reject / do not mark usable if stem or choices contain:

- “according to this chapter” / “по тексту этой главы”
- “UI-only and never takes part”
- “always means the same thing as”
- “enough to replace … with nothing else”

## Forbidden

- Using compiler for both quiz slots on a chapter by default
- Treating compiler output as equal quality to claim-mcq

## Skills to compose

- none (deterministic / code path)

## Skills to skip

- all quiz skills for this emergency item

## LLM brief

(empty — code compiles from theory)
