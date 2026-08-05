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
- **Docker / CLI / DevOps:** learner pastes a `Dockerfile`, shell commands, or config — never Python that returns Dockerfile text. Say so in `content`.
- Learner-facing task text (title, prompt, rubric) follows the course locale.
  For `domain=language`, sample phrases in the target language may appear inside the task,
  but instructions and rubrics stay in the course locale.
