# Skill: verbatim HTML → markdown

When converting scraped page text to markdown:

- Preserve code samples character-for-character inside fenced blocks.
- Keep numbered lists and bullet lists intact.
- Do not translate the article into another language.
- Do not add a preface like "Here is the article".
- Title comes from `<title>` / H1 when present; otherwise first strong heading.
