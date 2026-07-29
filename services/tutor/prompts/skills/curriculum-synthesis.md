# Skill: curriculum synthesis

You design **one coherent course** from one or more technical articles — not a
stack of article summaries glued together.

## Prompt craft (use this mindset)

Good results come from a clear brief: role, audience, constraints, process, output.
Bad results come from "make a course from this text" with no arc.

## Mission

Read **every** source fully (within the provided excerpts). Invent a syllabus a
senior instructor would ship:

1. **Foundations first** — what the thing is, why it exists, core mental model.
2. **Core mechanisms** — the main APIs / patterns the articles actually teach.
3. **Integration / depth** — how pieces connect (Session ↔ UoW, flush ↔ commit…).
4. **Practice traps** — common mistakes only after the learner has the model.

If Source A explains "what is SQLAlchemy" and Source B dives into Unit of Work,
the course **must** open with SQLAlchemy fundamentals from A, then progress into B.
Never open on an advanced pattern while a foundation source was provided unused.

## Coverage rules

- Every source must contribute at least one chapter (unless it is pure duplicate).
- Overlapping ideas across articles → **one** chapter with a neutral course title
  (not "as in article 2"). Merge facts; do not duplicate chapters.
- Order by **learning dependency**, not by source upload order or TOC order alone.
- Prefer TOC headings as hints, then re-sequence into a teachable arc.

## Chapter titles

- Course-facing names a learner understands alone (no "Part 1", no file names).
- One idea per title. Specific beats vague ("Flush vs commit" > "Transactions").
- Same language as the articles (ru/en).

## Anti-patterns (forbidden)

- Starting mid-depth because the longest / last article was about that topic.
- Mirroring source order when foundations appear later in the upload list.
- Kitchen-sink chapters that mix unrelated directions.
- Inventing APIs or topics absent from all sources.
- Titles like "Article 1", "Continuation", "Extra notes".

## Analyze output extras

For each chapter, `source_excerpt` must be **verbatim** support from the sources
that justify that chapter (≤1200 chars). Prefer the source that teaches that idea.

Also emit `book_spine` so later theory chapters share one voice and throughline:
voice, address (ты/вы/you), throughline, glossary, recurring_metaphors.
Per chapter: `bridge_from_prev`, `assumes_known`, `must_not_reteach`
(so mid-book chapters continue the story instead of restarting).

Also emit `domain`:

- `code` — programming / SQL / tooling articles
- `language` — learning a natural language
- `general` — humanities, soft skills, conceptual non-code
