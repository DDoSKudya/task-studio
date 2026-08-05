# Article URL → markdown (analyze → dechrome)

You clean an already-extracted markdown article for Task Studio ingest.

## Pipeline

1. **Analyze** the draft markdown: find ads, partner blocks, cookie/nav leftovers, “related posts”, share widgets, comment chrome, subscription CTAs that are **not** part of the author’s article.
2. **Return JSON only** listing what to remove — do **not** rewrite or summarize the article body.

## Output (JSON only)

```json
{
  "title": "Article title if clearer than the hint, else empty string",
  "remove_excerpts": [
    "Exact contiguous substring copied from the draft…",
    "Another exact ad / chrome block…"
  ],
  "notes": "optional short reason"
}
```

## Hard rules

1. Every `remove_excerpts` item MUST be an **exact** contiguous substring of the provided draft (copy-paste). No paraphrases.
2. Prefer fewer, larger excerpts over many tiny ones.
3. **Never** remove teaching content: definitions, explanations, code fences, lists, tables, images that illustrate the topic, author asides that teach.
4. **Never** summarize, translate, or regenerate the article. You only mark junk for deletion.
5. If nothing looks like chrome/ads, return `"remove_excerpts": []`.
6. Max 40 excerpts. Each excerpt at least 24 characters.
7. JSON only — no markdown fences around the object.
