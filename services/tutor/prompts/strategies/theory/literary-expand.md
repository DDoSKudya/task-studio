# literary-expand

## Status: canonical
## Applies to: all-providers
## Pack: author-full

## Pipeline

After section-blueprint exists, expand dense source prose into teachable markdown
while preserving the conceptual spine, figures, and key_claims.

## Gates

Same claim / figure / banned-opener gates as montage-preserve, plus:
- Worked example grounded in the excerpt
- Optional mermaid/table when `visual_plan` says so

## Forbidden

- Expanding without a blueprint
- Dropping `required_figures`

## Skills to compose

- `expand-dense-prose`, `diagram-craft`, `instructional-design`
- `anti-hallucination-source`, `negative-constraints`

## Skills to skip

- none

## LLM brief

Expand the excerpt into a clear teaching chapter for beginners. Keep the article’s
definitions, contrasts, and figures. Picture → example → name. No homework or MCQs
in theory. Locale follows the course request.
