# Skill: grade lab

For docker-lab / environment labs when the runner cannot execute (or `checker: llm`):

- Judge the learner's **report / notes / text** against the lab instructions and rubric.
- Pass when the report shows the required outcomes were achieved (commands run, expected state, answers to lab questions).
- Empty or placeholder reports → fail with high confidence.
- Do not invent infrastructure the lab never mentioned.
- Feedback: what evidence is missing from the report — not a full walkthrough of the lab.
