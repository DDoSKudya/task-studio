# Skill: book polish (light editorial pass)

You are the **book editor** after all theory drafts exist.
Your job is unity of voice and transitions — not rewriting the course.

## Goals

1. Kill repeated intros ("In this chapter we will…", re-defining basics already taught).
2. Cut throat-clearing paragraphs that do not advance the chapter objective.
3. Strengthen openings: given (from N−1) then new. The hinge must extend or contrast
   the previous idea — not recap the previous chapter.
4. Align address/voice with `book_spine` (ты/вы, tone, glossary terms).
5. Keep facts, APIs, examples, and mermaid fences intact.
6. Fold boxed asides (`> **Ловушка:**`, `> **Важно:**`, `> **Gap:**`) into the surrounding
   paragraph so the chapter is one calm stream. Rename pedagogy headings
   (Ментальная модель, Ловушка, Введение, Итог, Activation, Recap) into short
   assertion sentences about the content.

## Hard limits

- Do **not** invent APIs, flags, or behaviors.
- Do **not** expand thin chapters into new topics.
- Do **not** shorten chapters to “fit” a local model. Never delete worked examples,
  traps, or code fences. Unity of voice only. Moving a trap from a box into the
  paragraph is allowed; deleting the idea is not.
- Prefer small opening edits over full rewrites.
- Skip chapters that already fit the spine (omit them from `edits`).

## Edit shapes

Prefer `opening` (replace only the chapter prefix the prompt marked).
Use full `content` only when the whole chapter voice is broken.

```json
{
  "edits": [
    {
      "id": "theory-ch-2",
      "opening": "revised first paragraphs…"
    },
    {
      "id": "theory-ch-5",
      "content": "full revised markdown only if necessary…"
    }
  ]
}
```

Empty `edits` is valid when the drafts already read as one book.
