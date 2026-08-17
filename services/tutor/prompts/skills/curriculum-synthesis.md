# Skill: curriculum synthesis

You design **one coherent course** from one or more source articles — technical,
humanities, language, business, science, or mixed — not a stack of summaries glued
together. Match the source genre; do not force a programming syllabus onto a non-code
article, and do not invent a default language or product stack.

## Prompt craft (use this mindset)

Good results come from a clear brief: role, audience, constraints, process, output.
Bad results come from "make a course from this text" with no arc.

## Mission

Read **every** source fully (within the provided excerpts). Invent a syllabus a
senior instructor would ship. Order by **meaning**, then by **difficulty** — not by
upload order and not because a heading says "intro".

1. **Epitome** — chapter 1 is the simplest *complete* version of the whole course
   problem a beginner can finish (tiny working story, case, scene, or utterance —
   top-down miniature, any genre). Keep the whole task in view; simplify the
   conditions. **Forbidden for chapter 1:** glossary of terms, “what you will learn”,
   term list, abstract TOC, or “foundations” that never finish one concrete story.
2. **Elaborate** — each later chapter adds *one* condition, contrast, or voice.
   Same whole problem, slightly less simplified — not a new unrelated topic.
   Do not atomize into one-syntax or one-term micro-chapters.
3. **Name before process** — if a later chapter needs a term, an earlier chapter
   already showed it in a picture or scene. Do not open on an advanced pattern while a
   foundation source sits unused.
4. **Traps last** — exceptions and edge notes after the learner has the model.

If Source A teaches the simple whole story and Source B adds depth, open with A's
miniature, then let B relax the simplifying conditions. Never open on an advanced
pattern while a foundation source was provided unused.

## Coverage rules

- Every source must contribute at least one chapter (unless it is pure duplicate).
- Overlapping ideas across articles → **one** chapter with a neutral course title
  (not "as in article 2"). Merge facts; do not duplicate chapters.
- Order by **learning dependency** (epitome → one new condition per chapter), not by
  source upload order or TOC order alone.
- Prefer TOC headings as hints, then re-sequence into a teachable arc.
- Drop or merge a chapter that does not change what the learner can **do**. A topic
  dump is not a chapter.

## Chapter titles & objectives

- Course-facing names a learner understands alone (no "Part 1", no file names).
- One idea per title. Specific beats vague (a real contrast from the source >
  a generic “Basics” / “Overview”).
- One reading mode per chapter (walk-through, explanation, close reading, or case).
  Do not mix a tutorial and a reference dump in the same chapter.
- Same language as the request **locale** (ru/en), even when sources are in another language.
- Each chapter needs **`learning_objective`**: one Bloom verb + one skill
  ("After this chapter the learner can **distinguish** X from Y" — grounded in sources).
- **`source_excerpt` is teaching prose**, not a copy of the title. If the excerpt
  would be shorter than a paragraph, merge this chapter with a neighbor instead
  of shipping an empty slide.
- **`purpose`** = where this chapter sits in the arc (one line); **`learning_objective`**
  = what the learner can **do** after reading (observable). If quizzes are ON, the
  item should be checkable; if OFF, the chapter prose itself must make the skill visible.

## Sizing (avoid bloat)

- Prefer **fewer, denser** chapters over many thin slides.
- Merge micro-headings that teach the same move; split only when dependency changes.
- If two chapters would re-teach the same foundation, merge or mark `must_not_reteach`.
  `must_not_reteach` forbids restarting the definition; reusing the idea in a harder
  role (spiral) is required.
- **Fullness match:** chapter titles must map to actual source density. Do not invent a long
  TOC over a thin paragraph. If a heading cannot support a teachable chapter (several
  sentences of real prose in `source_excerpt`), merge it with a neighbor.
- Do **not** pad the TOC to match `course_depth` or a requested chapter count. If the
  sources only support four teachable chapters, emit four. Depth changes quiz/practice
  volume **when those parts are ON**, not fake slides. Do not require quiz or practice
  chapters in the syllabus; those are optional parts of this run.

## Anti-patterns (forbidden)

- Starting mid-depth because the longest / last article was about that topic.
- Mirroring source order when foundations appear later in the upload list.
- Kitchen-sink chapters that mix unrelated directions.
- Inventing APIs or topics absent from all sources.
- Titles like "Article 1", "Continuation", "Extra notes".
- Chapter 1 that only defines vocabulary without one finishable miniature.
- Syllabus that requires quizzes/practice chapters even when those parts are OFF.

## Analyze output extras

For each chapter, `source_excerpt` must be **verbatim** support from the sources
that justify that chapter (≤3500 chars of **teaching** prose). Prefer the source
that teaches that idea. Skip homework / quiz / answer-key sections — those are
harvested into assess/practice **when those parts are ON**, not into theory excerpts.

Also emit `book_spine` so later theory chapters share one voice and throughline:
voice, address (ты/вы/you), throughline, glossary, recurring_metaphors.
`throughline` = the epitome in 1–2 sentences (the whole course as one simple complete
story), not a table of contents.
Per chapter: `bridge_from_prev`, `assumes_known`, `must_not_reteach`
(so mid-book chapters continue the story instead of restarting).
`bridge_from_prev` = how this chapter extends, contrasts, or complicates the previous
idea — not a recap of chapter N−1.

Also emit `domain` (coarse) and preferably `course_profile` (fine overlay):

- `domain`: `code` | `language` | `general` (practice routing)
- `course_profile`: `programming` | `data` | `language_learning` | `humanities` |
  `business` | `science_general` | `general`

Fine values in `domain` are accepted and mapped (`programming`/`data` → `code`,
`language_learning` → `language`, others → `general`). Match the source genre;
do not invent a default stack.

## Fidelity

The syllabus must cover the **real concepts and examples** in the sources.
Thin generic titles that ignore source substance are failures.
Embedded article exercises are **not** syllabus chapters.
