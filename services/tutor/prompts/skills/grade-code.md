# Skill: grade code

For code / SQL steps (with or without a local harness):

- Judge against the written goal, sample data/schema in the prompt, starter template, and optional `rubric`.
- When no runner is available (unsupported language, missing packages, or `checker: llm`): grade **semantically** — would this solution satisfy the stated behavior? Prefer evidence from the task text over guessing APIs.
- For SQL: require a query that would produce the requested columns/rows on the described tables; ignore style (aliases, formatting) unless the task demands exact text.
- For programming: require behavior that matches the task; minor style issues are not fails.
- Empty, placeholder, or clearly unrelated code → fail with high confidence.
- Partial solutions that miss a required filter/column/edge → fail.
- Feedback: what is missing or incorrect relative to the task (not a full rewrite).
- Never claim you executed the code unless the submission itself shows an obvious match to stated I/O.
