# section-blueprint

## Status: canonical
## Applies to: all-providers

## Pipeline

1. Parse the article into document blocks (heading, paragraph, code, figure, list, table).
2. Seed chapters from H2/H3 sections (not sentence windows).
3. Merge thin sections; split oversized ones on subheadings.
4. Reorder with pedagogical rules (intro/basics early; production later; vendor marketing aside).
5. Emit a chapter blueprint JSON persisted in the course-build store.

## Gates

- Title length ≤ 70 characters
- Reject titles containing `![`, `***`, author intros (“my name is”), unclosed markdown
- Reject titles that are clearly first sentences of a paragraph (>10 words without a colon)
- Each chapter has `key_claims`, `source_block_ids`, optional `required_figures`, `visual_plan`

## Forbidden

- Using first sentence of a window as the chapter title (`sentence-windows`)
- Inventing chapters with no source blocks

## Skills to compose

- `curriculum-synthesis` (label/objective refinement only)

## Skills to skip

- none

## LLM brief

Propose short chapter titles (≤70 chars) and measurable objectives from the given
section summary. Do not paste paragraph openings. Do not invent facts or APIs
absent from the excerpt. Match the source genre. Output only the blueprint fields
requested by the stage schema.
