# Skill: verbatim HTML → markdown

When converting scraped page text to markdown:

- Preserve code samples character-for-character inside fenced blocks.
- Keep numbered lists and bullet lists intact.
- Do not translate the article into another language.
- Do not add a preface like "Here is the article".
- Title comes from `<title>` / H1 when present; otherwise first strong heading.
- For the **analyze** stage: mark ads/chrome as `remove_excerpts` only; never rewrite the body.
- Encyclopedia hosts (Wikipedia) may block bare browser GETs; the fetch pipeline may use
  the public REST HTML endpoint for `/wiki/…` pages — still treat the body as source text,
  never paraphrase it into a summary.
