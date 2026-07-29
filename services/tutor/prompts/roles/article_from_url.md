# Article URL → markdown

Convert fetched page HTML/text into a **verbatim** markdown article for the course-from-article pipeline.

## Goal

Given raw page content (HTML or plain text) and the source URL, produce a JSON object:

```json
{
  "title": "Article title",
  "content": "# Heading\n\nFull markdown body…"
}
```

## Rules

1. **Extract, do not invent.** Keep the author's wording. Do not summarize, paraphrase, or add commentary.
2. **Include the full article body** that a human reader would see as the main content: headings, paragraphs, lists, code blocks, tables (as markdown), blockquotes, captions.
3. **Drop chrome:** navigation, cookie banners, sidebars, related-posts widgets, footers, ads, share buttons, comment threads (unless they are clearly part of the article).
4. Prefer semantic markdown: `#` / `##` for headings, fenced code with language when obvious, `[text](url)` for links that belong to the article.
5. If the page is paywalled, empty, or not an article, still return JSON with the best title you can find and `content` explaining briefly in the page language that content could not be extracted (min ~40 chars).
6. Output **JSON only** — no markdown fences around the whole response, no prose outside the object.
7. `content` max ~80k characters; if longer, keep the start of the article and stop cleanly at a section boundary.
