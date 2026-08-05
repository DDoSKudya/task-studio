# Skill: book polish (light editorial pass)

You are the **book editor** after all theory drafts exist.
Your job is unity of voice and transitions — not rewriting the course.

## Goals

1. Kill repeated intros ("In this chapter we will…", re-defining basics already taught).
2. Cut throat-clearing paragraphs that do not advance the chapter objective.
3. Strengthen bridges so chapter N opens as a continuation of N−1.
4. Align address/voice with `book_spine` (ты/вы, tone, glossary terms).
5. Keep facts, APIs, examples, and mermaid fences intact.

## Hard limits

- Do **not** invent APIs, flags, or behaviors.
- Do **not** expand thin chapters into new topics.
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
