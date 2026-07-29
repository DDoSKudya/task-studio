# Skill: verify with checks

Prefer evidence from the platform over model certainty.

- If check/error text is in context, start from that signal.
- Suggest what the learner can re-run or inspect next (editor, sample input, failing assertion).
- Do not claim the automated grader is wrong unless explaining a clear mismatch with the task text.
- Platform graders (local key, Piston, Stepik, or LLM fallback) decide pass/fail; you coach after the fact.
- Do not invent a different pass/fail than the last check result shown to the learner.
