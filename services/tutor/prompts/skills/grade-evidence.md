# Skill: grade evidence

Confidence calibration (platform discards verdicts with confidence below the configured minimum, default **0.65**):

| Situation | confidence |
| --- | --- |
| Clear match / clear mismatch with task text or rubric | 0.75–0.95 |
| Clear empty / placeholder / off-topic submission | 0.85–0.95 |
| Plausible but incomplete evidence | 0.65–0.74 |
| Broken step (no text / unreadable choices) or uninterpretable submission | ≤ 0.64 |

Prefer an honest **usable** grade when the step is understandable. Do not sit at ≤ 0.54 just because no harness ran — that leaves the learner with “ungradable”.
