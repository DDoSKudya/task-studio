# source-figures-first

## Status: canonical
## Applies to: all-providers

## Pipeline

Collect image refs from article sources (`source_images` / markdown `![alt](url)`).
Attach the best matches to chapter blueprints as `required_figures`.
Emit them into theory / study steps in the manifest.

## Gates

- If the article has figures and a chapter scores a match → theory must include
  markdown image syntax for that URL (or an equivalent media step)
- Never leave a raw `![…]` fragment inside a **title**

## Forbidden

- Dropping all source figures on the local_course path
- Web image search (out of scope v1)

## Skills to compose

- none for attachment (code); `diagram-craft` only as fallback visual

## Skills to skip

- none

## LLM brief

When figures are listed for this chapter, keep them inline as markdown images with
the given URLs and useful alt text. Do not invent stock photos.
