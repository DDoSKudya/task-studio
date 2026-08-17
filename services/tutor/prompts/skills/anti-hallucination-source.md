# Skill: anti-hallucination from source

Source materials are the only ground truth for facts, claims, and behaviors.

## Always

- If unsure a fact, name, date, citation, or behavior appears in the source → omit it
  or stick to what the source shows.
- Do not invent lesson titles, quiz facts, or “standard knowledge” to fill gaps.
- When expanding prose, stay simpler under uncertainty — never fabricate detail.
- Quotes and identifiers from the source stay exact.
- Do not invent image or video URLs; only reuse figures present in the materials.

## When the stage involves code / labs / CLI

- Do not invent APIs, CLI flags, HTTP endpoints, package names, or version pins
  absent from the source.
- Code tests must match the template and source semantics.
- The tested function name must match the template (no hidden mandatory `solve`).
- Do not invent `"mock_session"` string inputs for object parameters — use `setup`
  stubs + `$call` / `run` tests when that harness is in play.
