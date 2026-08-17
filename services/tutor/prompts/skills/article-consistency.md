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
      "summary": "What differs or conflicts (focus, depth, APIs, recommendations)",
      "sources": ["Source 1 title", "Source 2 title"]
    }
  ]
}
```

## Rules

- `similarity` is 0..1 (topic overlap / complementary fit).
- `related=false` only if sources clearly belong to **unrelated** subjects (e.g. pathlib vs asyncio).
- Always fill `deviations` when articles share a topic but **differ in emphasis, depth, or structure advice**
  (e.g. one is webhooks/Pydantic, another is package layout/APIRouter) — even without hard API contradictions.
- For same-topic complementary articles: `related=true`, `similarity` typically **0.7–0.9**, and **at least one**
  deviation that names the different accents (so the author can confirm merging them).
- List hard contradictions too (incompatible APIs, mutually exclusive advice).
- Do **not** invent facts. Mild typography/length-only differences without topic drift are not deviations.
- Keep `deviations` short (max 5). Language = locale of the request.
