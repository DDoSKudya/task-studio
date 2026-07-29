# Skill: expand dense prose

Turn compressed or thin technical article text into a **teachable** theory chapter —
the kind that builds a mental model for someone who has not lived this topic yet.

## One chapter = one idea

This chapter covers **exactly one** learning move (one concept, contrast, or technique).
Do not smuggle neighboring topics into the same chapter. If the excerpt mixes themes,
teach only the chapter title; leave the rest for other chapters.

## Beginner-first pedagogy (even for dense sources)

Assume the reader may know adjacent tools but **not** this idea. Always include:

1. **Mental model** — a concrete analogy or picture of how the parts fit (not marketing fluff).
2. **Worked example** — small, runnable or walk-through; prefer real snippets from the source.
3. **Traps** — 1–2 mistakes beginners make when the article is sparse or assumes expertise.
4. **Gap fill** — if the excerpt is thin, incomplete, or jumps steps: fill the missing
   prerequisites and “why it works” from **general domain knowledge**, but never invent
   APIs, flags, version numbers, or product claims that are not in the source.
   Mark pedagogical bridges plainly (e.g. a short callout) when you add connective tissue.

Pedagogical analogies are allowed. Fabricated library APIs are forbidden.

When a **book spine** is provided in the user message, treat the course as one book:
reuse the throughline and glossary, keep the same address/voice, and never re-open
topics listed in `must_not_reteach`. Use `bridge_from_prev` as the opening hinge.

## Writing craft

- **Voice:** confident, concrete, slightly conversational. Second person ("you") is fine.
- **Open with friction:** a mistake, a confusing API call, a failed mental model — then resolve it.
- **One claim per section:** each `##` heading advances a single point.
- **Show, then name:** example or vignette first, terminology second.
- **Short paragraphs:** 2–4 sentences. Prefer line breaks over walls of text.
- **Cut filler:** no "in this chapter we will…", "it is important to note…".

## Structure (adapt, do not pad)

1. Hook / pain the reader already feels (3–6 sentences)
2. Mental model in plain language
3. Core definition (one crisp claim)
4. Worked example — keep real code from the article when present
5. Mermaid diagram when the chapter is structural (see diagram-craft)
6. Edge / neighboring tool **only if** it clarifies *this* idea
7. Traps specific to this idea
8. Short recap (3–5 bullets, no new facts)

Use `##` / `###` headings. Prefer several small sections over one long mash.
Optional callouts as markdown blockquotes for traps or “gap fill” notes:

> **Ловушка:** ...
> **Важно:** ...
> **Gap:** ...

## Few-shot shape (bad → good)

Bad (do not write like this):

- "В этой главе мы рассмотрим Session. Session — это объект. Он важен."
- Pasted code with zero connective tissue.

Good (aim for this texture):

- Open with a concrete failure ("сохранили — в БД пусто").
- Give a mental model (Session = desk).
- Callout the trap: `add()` ≠ INSERT.
- Then a short faithful code fence.

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

## Quality

- Expand explanations; do not paste the article unchanged.
- Keep factual API names and signatures from the source.
- Preserve useful tables and code fences; add connective tissue around them.
- Length: enough to teach **this** chapter goal (roughly 500–1100 words), not a book dump.
- Output field `content` is a markdown string for a theory step.
