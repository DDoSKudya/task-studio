# Article consistency (multi-source)

When several source articles are provided, judge whether they form one coherent course topic.

## Output JSON only

```json
{
  "related": true,
  "similarity": 0.0,
  "shared_topic": "short topic label",
  "deviations": [
    {
      "summary": "What conflicts or drifts (facts, APIs, recommendations)",
      "sources": ["Source 1 title", "Source 2 title"]
    }
  ]
}
```

## Rules

- `similarity` is 0..1 (topic overlap / complementary fit).
- `related=false` if sources clearly belong to different unrelated subjects.
- List only **meaningful** deviations: contradictory claims, incompatible APIs, mutually exclusive advice.
- Do **not** invent deviations. Mild style/length differences are not deviations.
- Complementary coverage of the same topic (basics + advanced) is OK — `related=true`, empty `deviations`.
- Keep `deviations` short (max 5). Language = locale of the request.
