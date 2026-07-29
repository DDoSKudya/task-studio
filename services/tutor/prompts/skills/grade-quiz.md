# Skill: grade quiz

For multiple-choice / single-choice quiz steps:

- Read the question and every choice carefully.
- The submission is a `choice_index` (0-based). Map it to the corresponding choice text when choices are present.
- Pass only if that choice is the best correct answer given the question.
- If choices are missing or malformed, still grade from the question text and submitted index when possible; keep confidence honest (typically 0.5–0.75), never invent options.
- Feedback may say why the chosen option is wrong/right in general terms; do not write “правильный индекс = …”.
