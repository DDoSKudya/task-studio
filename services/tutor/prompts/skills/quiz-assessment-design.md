# Skill: quiz assessment design

Only when this run includes quizzes. Design multiple-choice items that **actually
check understanding** after reading the theory. If quizzes are OFF, do not emit items.

## Alignment (critical)

- Each quiz must test the **chapter `learning_objective`** (Apply / Analyze), not unrelated trivia.
- Stem should require using the mental model from theory — not recall of wording from the title
  (a decision, contrast, or next step — across any genre).
- If theory taught a contrast, distractors = plausible wrong side of that contrast
  (technical, interpretive, grammatical, or business — matching the chapter).

## Rules

- Prefer **harvested article checks** first (source MCQs / open questions adapted into
  the course locale) before inventing new stems.
- Exactly **4** choices; exactly **one** correct (`answer` = 0-based index).
- **Vary** the correct index across items — do not always put the right choice at `0`.
- Choices must be similar in length, tone, and specificity (no “obviously correct” long option).
- Distractors = misconceptions a reader of **this chapter** could actually hold
  (wrong side of a contrast, wrong next step), not jokes or other-course trivia.
- Avoid: “all of the above”, “none of the above”, double negatives, trick wording.
- Prefer apply/analyze over trivia (“what year…”, “who invented…”).
- Early chapters may lean identify/distinguish; late chapters choose/justify —
  always grounded in **this** chapter's theory.
- From the second chapter onward, if you emit 2+ items, one item applies an **earlier**
  chapter idea *inside this chapter's situation* (spacing). Not a recap of chapter 1.
- Forbidden: “what is the main goal of this chapter”, stems that only paraphrase the title.
- Stem contains the full question; choices stay short.
- Do **not** mark the correct choice with bold/emoji/asterisks in the text.
- Never store letter-only choices (`A`,`B`,`C`,`D`) or Cyrillic letter labels alone.

## Output shape per quiz step

```json
{
  "id": "quiz-1",
  "kind": "quiz",
  "title": "Which claim fits",
  "question": "Which next step matches this chapter's model?",
  "choices": [
    "A plausible misconception from the chapter",
    "The correct next step grounded in the theory",
    "Another plausible misconception",
    "A third misconception, not a joke"
  ],
  "answer": 1
}
```

Choices are **full answer text**, never bare letters (`A` / `B` / `C` / `D`) and never
prefixed with `A)` labels. Replace the placeholder choice strings with real claims
from **this** chapter's medium (code, argument, language form, business metric, …).