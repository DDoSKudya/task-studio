# Skill: course stage JSON

Each pipeline stage returns one JSON object only.

**Course locale (mandatory):** learner-facing text follows the request `locale`
(`ru` / `en`), not the language of the source articles. Sources may be any language.

## Stage: analyze

First pass — syllabus skeleton (short JSON):

```json
{
  "pack_id": "slug",
  "title": "Course title",
  "locale": "ru",
  "domain": "code",
  "course_profile": "programming",
  "audience_level": "middle",
  "outcomes": ["measurable outcome 1", "outcome 2"],
  "book_spine": {
    "voice": "calm second-person essayist",
    "address": "ты",
    "throughline": "one recurring mental model that ties the arc",
    "glossary": [{"term": "key term", "sense": "short sense from the sources"}],
    "recurring_metaphors": ["one metaphor from the source world"]
  },
  "chapters": [
    {
      "id": "ch-foundations",
      "title": "Short assertion title for chapter 1",
      "learning_objective": "After this chapter the learner can <verb> <skill>"
    }
  ]
}
```

Follow-up passes may request one chapter detail object (`purpose`, `learning_objective`,
bridges, `source_excerpt` ≤3500 chars).

`domain` (required, coarse — practice routing):

- `code` — software / data / APIs; practice = code ladder when profile is technical
- `language` — natural-language learning; practice = open `task` ladder
- `general` — humanities / business / science / mixed conceptual; open `task` ladder

`course_profile` (strongly preferred — picks `domain-*.md` overlay):

- `programming` | `data` | `language_learning` | `humanities` | `business` |
  `science_general` | `general`

If you only know the fine genre, you may put it in `domain`; the harness maps
`programming`/`data` → `code`, `language_learning` → `language`, other fine values →
`general`. Prefer emitting **both** fields when sure.

Max 12 chapters. Aim for **6–12** when multiple sources exist.

**Book unity (critical):**

- The course must read as **one book**, not a zip of essays.
- `book_spine` is the shared editorial brief for every theory chapter (voice, address, throughline, glossary, metaphors).
- Later chapters use `assumes_known` / `must_not_reteach` / `bridge_from_prev` so they continue the arc instead of re-introducing foundations.

**Curriculum rules (critical):**

- Build **one** progressive course: epitome (simplest whole task) → one new
  condition per chapter → traps.
- Cover **all** sources; do not skip an intro article because another source is denser.
- Re-order freely for learning dependency (ignore upload order).
- One idea per chapter; split mixed TOC headings.
- Overlaps across articles → merge into one well-named chapter.
- `purpose` = one short line: role of this chapter in the arc.
- `learning_objective` = observable skill after the chapter (Bloom verb + one capability).
  Every part that is ON for this run must align to it. Do not emit quizzes or practice
  when those parts are OFF, and do not plan them as required syllabus steps.
- `source_titles` = which sources feed this chapter (use exact source titles from the prompt).
- `source_excerpt` supports **only** that chapter; verbatim from those sources.
- Course `title` names the whole subject (not a single advanced subtopic).
- Outcomes map to the arc (beginner can state them; advanced ones come later).

## Stage: theory_chapter

```json
{
  "id": "theory-ch-intro",
  "kind": "theory",
  "title": "...",
  "content": "markdown..."
}
```

`content` is plain markdown. Code fences contain source code only (no HTML / highlighter markup).
Teach this chapter in context of the syllabus (assume prior chapters were read; do not re-teach them).
**Never** put homework, quizzes, «Задание», check-yourself, or answer keys in `content` —
those are separate assess/practice steps.

## Stage: book_polish

Light editorial pass after all theory drafts. Unify openings/voice; do not invent APIs.

```json
{
  "edits": [
    { "id": "theory-ch-2", "opening": "revised opening paragraphs…" },
    { "id": "theory-ch-5", "content": "full revised markdown only if needed…" }
  ]
}
```

Prefer `opening` over full `content`. Omit unchanged chapters. Empty `edits` is fine.

## Stage: quizzes

Prefer one quiz per call when the harness asks for a single item:

```json
{ "quiz": { "id": "quiz-1", "kind": "quiz", "title": "...", "question": "...", "choices": ["full text one", "full text two", "full text three", "full text four"], "answer": 0 } }
```

Legacy batch form `{ "quizzes": [ ... ] }` is also accepted. Cover the whole arc; no invented facts.

## Stage: code_ladder

Prefer one task per call when the harness asks for a single level:

```json
{
  "task": {
    "id": "code-easy",
    "kind": "code",
    "title": "...",
    "content": "What to build.\\n\\n**Input:** ...\\n\\n**Output:** ...\\n\\n**Constraints:** ...",
    "runtime": "python",
    "runtime_version": "3.12",
    "template": "def domain_named_fn(...):\n    ...\n",
    "entrypoint": "domain_named_fn",
    "setup": "",
    "dependencies": ["httpx>=0.27"],
    "tests": [{"input": [], "output": null}],
    "level": "easy"
  }
}
```

`content` must spell out accepted inputs and expected return shape for the learner;
do not hide the contract only inside the template docstring.
Do not paste `requirements.txt` / `package.json` samples in `content` — list packages in `dependencies`.

Batch `{ "tasks": [ ... ] }` is accepted only when asked. When tests cannot honestly run in a sandbox, set `"checker": "llm"` and a `"rubric"`.

## Stage: task_ladder

For `domain` = `language` or `general` (and non-technical `course_profile`), prefer one open task per call:

```json
{
  "task": {
    "id": "task-easy",
    "kind": "task",
    "title": "...",
    "content": "brief + constraints",
    "rubric": "- criterion 1\n- criterion 2",
    "exemplar": "optional model answer for grader only"
  }
}
```
