# gates-first

## Status: canonical
## Applies to: all-providers

## Pipeline

Run deterministic gates **before** LLM polish:

1. Structure (L0) — titles, refs, caps  
2. Content (L1) — claims, banned openers  
3. Visual (L2) — figures / mermaid  
4. Assess (L3) — quiz/practice shape  
5. Optional polish / reinforce

## Gates

- Polish skipped for capacity must not hide L0 title failures
- Fail or warn with explicit strategy IDs in logs

## Forbidden

- Shipping packs that fail L0 because polish “looked done”

## Skills to compose

- `chapter-quality-gate` when reinforce rounds are enabled

## Skills to skip

- none

## LLM brief

(empty for the gate runner; critique skills apply only in reinforce rounds)
