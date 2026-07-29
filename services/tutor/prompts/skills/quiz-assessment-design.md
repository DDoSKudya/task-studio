# Skill: quiz assessment design

Design multiple-choice items that **actually check understanding** after reading the theory.

## Rules

- Exactly **4** choices; exactly **one** correct (`answer` = 0-based index).
- Choices must be similar in length, tone, and specificity (no “obviously correct” long option).
- Distractors = plausible misconceptions from the material (wrong API, wrong mental model).
- Avoid: “all of the above”, “none of the above”, double negatives, trick wording.
- Prefer apply/analyze over trivia (“what year…”, “who invented…”).
- Stem contains the full question; choices stay short.
- Do **not** mark the correct choice with bold/emoji/asterisks in the text.

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
