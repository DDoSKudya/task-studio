# montage-preserve

## Status: canonical
## Applies to: all-providers
## Pack: preserve-7b (primary)

## Pipeline

Assemble theory from blueprint `source_block_ids` plus short bridging sentences.
Inline required figures. Prefer quotation / tight paraphrase over rewrite-from-scratch.

## Gates

- Every `key_claim` appears in the theory (token / phrase overlap)
- No banned openers (“deep dive”, “let’s move on”, emoji cheerleading)
- No author-bio dumps as lesson body
- Length under pack continue/token caps
- Runtime / language of code fences matches the course runtime when showing app code

## Forbidden

- Full literary rewrite that drops claims and figures
- Long continue-loops that paste unrelated stacks (e.g. PHP in a JS course)

## Skills to compose

- `anti-hallucination-source`, `negative-constraints`
- `diagram-craft` when `visual_plan` requires mermaid and no source figure

## Skills to skip

- `expand-dense-prose` (conflicts with montage)
- `instructional-design` on preserve packs (strategy briefs own chapter method)

## LLM brief

Montage this chapter from the provided source blocks. Add brief bridges only.
Keep claims, commands, quotes, and figures from the source. Do not restart the
chapter or invent facts, APIs, or citations. Match the source genre (technical,
humanities, language, …). No homework or quiz blocks inside theory.
