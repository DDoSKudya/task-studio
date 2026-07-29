# Skill: course stage JSON

Each pipeline stage returns one JSON object only.

## Stage: analyze

First pass — syllabus skeleton (short JSON):

```json
{
  "pack_id": "slug",
  "title": "Course title",
  "locale": "ru",
  "domain": "code",
  "audience_level": "middle",
  "outcomes": ["measurable outcome 1", "outcome 2"],
  "book_spine": {
    "voice": "calm second-person technical essayist",
    "address": "ты",
    "throughline": "one recurring mental model that ties the arc",
    "glossary": [{"term": "Session", "sense": "desk before commit"}],
    "recurring_metaphors": ["desk / warehouse"]
  },
  "chapters": [
    { "id": "ch-foundations", "title": "What SQLAlchemy is and why Session exists" }
  ]
}
```

Follow-up passes may request one chapter detail object (`purpose`, bridges, `source_excerpt` ≤500 chars).

`domain` (required):

- `code` — programming / SQL / APIs; practice = code ladder
- `language` — language learning (English etc.); practice = open `task` ladder
- `general` — humanities / soft skills / conceptual; practice = open `task` ladder

Max 12 chapters. Aim for **6–12** when multiple sources exist.

**Book unity (critical):**

- The course must read as **one book**, not a zip of essays.
- `book_spine` is the shared editorial brief for every theory chapter (voice, address, throughline, glossary, metaphors).
- Later chapters use `assumes_known` / `must_not_reteach` / `bridge_from_prev` so they continue the arc instead of re-introducing foundations.

**Curriculum rules (critical):**

- Build **one** progressive course: foundations → core → depth → traps.
- Cover **all** sources; do not skip an intro article because another source is denser.
- Re-order freely for learning dependency (ignore upload order).
- One idea per chapter; split mixed TOC headings.
- Overlaps across articles → merge into one well-named chapter.
- `purpose` = one short line: role of this chapter in the arc.
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
{ "quiz": { "id": "quiz-1", "kind": "quiz", "title": "...", "question": "...", "choices": ["a","b","c","d"], "answer": 0 } }
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
    "content": "brief",
    "runtime": "python",
    "runtime_version": "3.12",
    "template": "def domain_named_fn(...):\n    ...\n",
    "entrypoint": "domain_named_fn",
    "setup": "",
    "tests": [{"input": [], "output": null}],
    "level": "easy"
  }
}
```

Batch `{ "tasks": [ ... ] }` is accepted only when asked. When tests cannot honestly run in a sandbox, set `"checker": "llm"` and a `"rubric"`.

## Stage: task_ladder

For `domain` = `language` or `general` (no code practice), prefer one open task per call:

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
