# claim-mcq

## Status: canonical
## Applies to: all-providers

## Pipeline

Build 1–2 MCQs per chapter from blueprint `key_claims`. Distractors are
misconceptions, not nonsense. Normalize choices to full text (never bare A/B/C/D).

## Gates

- Question length ≥ 25 characters
- Four distinct non-empty choices; not letter-only labels
- Correct index valid; avoid clustering all answers at 0 when salt is available
- Cross-topic similarity ≥ 0.85 → regenerate or drop
- Stem must not match forbidden compiler patterns (see theory-compiler)

## Forbidden

- Letter-only choices (`A`, `B`, `C`, `D`) as the stored choice text
- Duplicate stems within or across topics without regeneration

## Skills to compose

- `quiz-assessment-design`, `course-stage-json`, `negative-constraints`

## Skills to skip

- none

## LLM brief

Write MCQs that test the listed key claims for this chapter's genre. Equal-weight
choices as full text (never bare A/B/C/D). One best answer. Distractors = typical
mistakes from the chapter — misconceptions, not nonsense or other-course trivia.
Output JSON per stage schema only.
