# Skill: quiz assessment design

Design multiple-choice items that **actually check understanding** after reading the theory.

## Alignment (critical)

- Each quiz must test the **chapter `learning_objective`** (Apply / Analyze), not unrelated trivia.
- Stem should require using the mental model from theory — not recall of wording from the title.
- If theory taught a contrast (flush vs commit), distractors = plausible wrong side of that contrast.

## Rules

- Exactly **4** choices; exactly **one** correct (`answer` = 0-based index).
- Choices must be similar in length, tone, and specificity (no “obviously correct” long option).
- Distractors = plausible misconceptions from the material (wrong API, wrong mental model).
- Avoid: “all of the above”, “none of the above”, double negatives, trick wording.
- Prefer apply/analyze over trivia (“what year…”, “who invented…”).
- Stem contains the full question; choices stay short.
- Do **not** mark the correct choice with bold/emoji/asterisks in the text.
- When the harness provides **harvested article checks**, adapt those first
  (especially source MCQs / open questions) before inventing new stems.

## Output shape per quiz step

```json
{
  "id": "quiz-1",
  "kind": "quiz",
  "title": "...",
  "question": "...",
  "choices": ["A", "B", "C", "D"],
  "answer": 1
}
```
