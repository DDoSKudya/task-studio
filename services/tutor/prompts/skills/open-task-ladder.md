# Skill: open task ladder

Create practice tasks for **non-code** courses (languages, humanities, soft skills): free-text answers graded by AI against a rubric.

## Ladder

| Level | Goal |
| --- | --- |
| easy | Apply one idea from the material (short answer / rewrite / fill) |
| medium | Combine ideas; handle an edge case or nuance |
| hard | Realistic production of the skill (email, translation, short essay, critique) |

## Each task must include

- `id` like `task-easy`, `kind`: **`task`**
- `title`, short `content` brief (what to produce, constraints, audience)
- `rubric`: bullet criteria the grader will use (3–6 points, concrete)
- Optional `exemplar`: model answer for the grader only (never shown to the learner in UI)
- Do **not** invent fake code `tests` or `template` for these steps

## Quality

- Tasks must be answerable from the article / theory alone.
- Rubric must match the brief — no hidden criteria.
- Difficulty must increase across the three tasks.
- Prefer the same language as the course locale unless the course is language-learning (then the target language is explicit in `content`).
