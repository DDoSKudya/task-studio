# Skill: open task ladder

Only when this run includes practice. Create practice tasks for **non-code** courses
(languages, humanities, soft skills): free-text answers graded by AI against a rubric.
If practice is OFF, do not emit tasks.

## Ladder

When several tasks belong to **one** chapter, keep the **same** skill and fade
scaffold (do not jump to a new topic).

| Level | Goal |
| --- | --- |
| easy | Apply one idea from this chapter (short answer / rewrite / fill) |
| medium | Same skill; edge case or nuance from this chapter |
| hard | Same skill as a short authentic product (email, translation, critique) |

## Each task must include

- `id` like `task-easy`, `kind`: **`task`**
- `title`
- `content`: clear brief the learner reads first — goal, accepted input / materials,
  expected deliverable, constraints (length, tone, format). Prefer short markdown
  sections over a single vague sentence.
- `rubric`: bullet criteria the grader will use (3–6 points, concrete)
- Optional `exemplar`: model answer for the grader only (never shown to the learner in UI)
- Do **not** invent fake code `tests` or `template` for these steps

## Quality

- Tasks must be answerable from the article / theory alone.
- Rubric must match the brief — no hidden criteria.
- Difficulty must increase across the three tasks.
- Learner-facing task text (title, prompt, rubric) follows the course locale.
  For language-learning profiles, sample phrases in the target language may appear
  inside the task, but instructions and rubrics stay in the course locale.
