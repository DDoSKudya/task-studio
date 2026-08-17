# Output contract (theory prose call)

This call is **not** a JSON stage. Override any JSON-only instruction in the role.

Return **plain markdown only** for one theory chapter:

- No JSON object, no outer markdown fence around the whole chapter, no preamble or meta commentary.
- Write the full chapter once; if truncated the system will ask you to **continue**, not restart.
- Cap at **≤6** `##` sections; each heading appears **at most once**.
  Headings are short assertions (the takeaway), not lesson-frame labels.
- Never repeat the same section title, paragraph block, or worked example.
- Write **calm running prose**, like a textbook chapter: one voice, one stream.
  Do not use blockquote callouts (`> **Ловушка:**`, `> **Важно:**`, `> **Gap:**`)
  and do not title sections Activation / Mental model / Trap / Recap / Введение / Итог.
- Do not add standalone «Заключение» / «Summary» sections that re-teach earlier points —
  end with one short bridge sentence toward the next chapter instead.
- Theory = teaching prose only (no homework, quizzes, answer keys).
- If quizzes/practice are OFF, do not add self-checks or "try this" tasks to compensate —
  keep the worked example in the chapter. Never shrink because later stages are missing.
- Later fragments of the same chapter **continue** the argument — no second introduction.
