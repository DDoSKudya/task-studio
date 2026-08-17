# mermaid-architecture

## Status: canonical
## Applies to: all-providers

## Pipeline

When a foundation / flow / architecture chapter has no source figure, require one
```mermaid
fence (or a markdown compare table) per `visual_plan`.

## Gates

- Fence tag matches body (`mermaid` for diagrams)
- Diagram is present when `visual_plan.type` requests it and no figure was attached

## Forbidden

- Labeling application code as `sql` / wrong fence tags

## Skills to compose

- `diagram-craft`

## Skills to skip

- none

## LLM brief

Add one clear mermaid diagram (or compare table) that matches visual_plan.
Keep it small and accurate to the excerpt. No decorative diagrams without meaning.
