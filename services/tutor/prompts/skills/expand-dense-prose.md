# Skill: expand dense prose

Turn compressed or thin source text into a **teachable** theory chapter —
the kind that builds a mental model for someone who has not lived this topic yet.

## One chapter = one idea

This chapter covers **exactly one** learning move (one concept, contrast, or technique).
Do not smuggle neighboring topics into the same chapter. If the excerpt mixes themes,
teach only the chapter title; leave the rest for other chapters.
Later fragments of the **same** chapter continue that move — no second hook, no recap.

## Beginner-first pedagogy (even for dense sources)

Assume the reader may know adjacent tools but **not** this idea. Weave these into
**running prose** — do not label them as sections or boxes:

1. A concrete picture of how the parts fit (one analogy, then real names).
2. A worked example — small, runnable or walk-through; prefer real snippets from the source.
3. One or two beginner mistakes, as ordinary sentences ("часто путают…"), not a framed aside.
4. If the excerpt jumps a step, fill the gap from general domain knowledge, but never invent
   APIs, flags, version numbers, or product claims. A missing step is a sentence, not a "Gap" box.

Pedagogical analogies are allowed. Fabricated library APIs are forbidden.

## Analogies (one, then drop it)

- One picture from the source's world — not a mixed bag of metaphors.
- The analogy explains the mechanism in 2–4 sentences, then you use the real names.
- Never a second metaphor for the same idea. Never an analogy that does not map onto a source fact.
- If the excerpt already has a clear example, prefer that example over a new analogy.
- Do not pad: no extra paragraphs whose only job is to sound friendly.

When a **book spine** is provided in the user message, treat the course as one book:
reuse the throughline and glossary, keep the same address/voice, and never re-open
topics listed in `must_not_reteach` as definitions (you may reuse them harder).
Use `bridge_from_prev` as the opening hinge: given (known) then new.

## Writing craft

- **Voice:** calm textbook, one register for the whole chapter. Address the learner as
  **ты** (ru) or **you** (en) unless `book_spine.address` says otherwise. Never mix ты/вы.
- **One calm stream:** the chapter reads like a book, not a worksheet. Paragraphs follow
  each other. Do not chop the argument into labeled frames (Activation, Mental model,
  Trap, Key takeaways) and do not wrap asides in blockquotes (`> **Ловушка:**`,
  `> **Важно:**`, `> **Gap:**`). A trap is a sentence in the same voice.
- **Open given → new:** after chapter 1, first sentences reuse what the prior chapter
  already taught, then one new complication. Chapter 1 may open on friction.
  A one-sentence organizer may sit in the first paragraph — it is not a recap and not
  a boxed "objectives" list.
- **Assertion headings:** each `##` is a short complete sentence that *is* the takeaway
  ("Session не пишет строку до flush"), not a topic label ("Сессии", "Пример",
  "Основная идея"). Forbidden as headings: Введение, Теория, Ментальная модель,
  Демонстрация, Ловушка, Итог, Заключение, Activation, Recap, Key takeaways.
- **Show, then name:** example or vignette first, terminology second.
- **Short paragraphs:** 2–4 sentences. Prefer line breaks over walls of text.
- **Cut filler:** no "in this chapter we will…", "it is important to note…".
- **One reading mode** for the whole chapter: either you walk the reader through a doing,
  or you explain why something is so, or you close-read a passage. Do not switch from
  tutorial to reference dump mid-chapter.

## Structure (invisible craft — do not print these labels)

Follow the chapter **`learning_objective`**. The moves below are the author's order,
not headings on the page:

1. Open on prior knowledge or a failure (no course-wide intro).
2. One concrete picture, then the real names.
3. Worked example from the source. After a code/scene fence, explain **in the order of
   the steps shown** — not a recap after a wall of code. The sentence that names a call
   sits next to that fence (before or immediately after), never a section later.
4. If two things are contrasted, a small markdown **table** beats a diagram. Draw
   mermaid only for flow, layers, or state (see diagram-craft). Caption in the next
   sentence. At most one source figure, `![alt](url)` copied exactly.
5. One beginner mistake, in the same prose.
6. Close with one bridge sentence toward the next chapter — not a summary section.

Cap at **≤6** `##` sections, roughly similar length. One giant section plus five stubs
is a failed chapter. If a section repeats a prior chapter, delete it.

If the opening example is a complete working slice the reader cannot yet fully unpack,
say so in one calm sentence and keep going — later chapters name the parts. Do not
turn that into a boxed disclaimer.

## Few-shot shape (bad → good)

Bad (do not write like this):

- "В этой главе мы рассмотрим Session. Session — это объект. Он важен."
- Headings «Ментальная модель» / «Ловушка» and `> **Важно:**` callouts.
- Pasted code with zero connective tissue, then a recap paragraph.

Good (aim for this texture):

- `## Session ещё не пишет строку в таблицу`
- Open on "сохранили — в БД пусто", picture the desk, drop the metaphor, then the fence.
- After the fence: what `add()` does, then what `flush()` does, in that order.
- "Частая путаница — принять `add()` за INSERT." Same paragraph voice, no box.

## Code fences

- Use fenced markdown with a **correct** language tag matching the body:
  - Python / SQLAlchemy / ORM session code → ` ```python `
  - Raw SQL statements (`SELECT`, `WITH name AS (`, `INSERT`…) → ` ```sql `
  - JavaScript / TypeScript → ` ```javascript ` or ` ```typescript `
  - Structure diagrams → ` ```mermaid ` (see diagram-craft)
- Never label Python as `sql` or leave ORM snippets as bare/untagged/`text`.
  Classic trap: `with Session(...) as session:` is **Python**, not SQL `WITH`.
- Code must be **plain source text only** — never HTML, never highlighter tokens,
  never spans/classes like `tok-kw`, `tok-str`, or similar.
- Keep signatures and APIs faithful to the source article.
- Name each API or command in teaching prose **next to** the fence so a reader
  who skips the code still meets the idea. Do not park the explanation in a later section.
- **Fence integrity (critical):** one example = one fence. Do not close ``` in the middle
  of a class/function and continue methods as normal paragraphs — Markdown will corrupt
  `__init__` / `__set__` / `__new__`. Write the whole snippet, then close the fence, then explain.
- Prefer short complete examples (≤40 lines) over multi-page dumps. If you need a second
  example, finish the first fence, write a short bridge sentence, open a new fence.

## Source images

- When the prompt lists **Source figures**, you may paste **at most 1–2** markdown images
  into this chapter — only if they illustrate the current idea.
- Copy the `![alt](url)` line **verbatim**. Do not invent, rewrite, or hotlink unrelated assets.
- Prefer diagrams/screenshots over logos, avatars, and decorative banners.
- Videos belong in separate `kind: video` steps — never embed video iframes in theory markdown.

## Quality

- Expand explanations; do not paste the article unchanged.
- Keep factual API names and signatures from the source.
- Preserve the article's conceptual spine (definitions, contrasts, real examples) —
  do not thin it into generic fluff that could fit any topic.
- Preserve useful tables and code fences; add connective tissue around them.
- Length: enough to teach **this** chapter goal from the excerpt (roughly
  600–1400 words of prose when the source is rich). Prefer full coverage over
  aggressive shortening; never pad with filler.
- **Match excerpt richness:** a long excerpt → a long teachable chapter. Do not compress
  a 1500-word excerpt into three sentences. A thin excerpt stays shorter — still teach,
  do not invent neighboring topics to fill space.
- Output field `content` is a markdown string for a theory step.
- **No drills in theory:** worked examples are fine; numbered assignments, quizzes,
  «Проверьте себя», and answer keys are forbidden here.
