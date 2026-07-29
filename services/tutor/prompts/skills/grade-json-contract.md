# Skill: grade JSON contract

Respond with a single JSON object, exactly these keys:

```json
{
  "passed": true,
  "confidence": 0.0,
  "feedback": "short learner-facing reason",
  "rationale": "brief private grader note"
}
```

- `passed`: boolean
- `confidence`: number from 0.0 to 1.0 (how sure you are)
- `feedback`: non-empty string for the UI (no code dump longer than ~4 lines)
- `rationale`: short internal note (may mention criteria checked)

No other keys. No trailing commentary.
