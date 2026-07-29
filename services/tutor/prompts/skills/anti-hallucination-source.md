# Skill: anti-hallucination from source

The article is the only ground truth for APIs and behaviors.

- If unsure whether a method exists → omit it or stick to what the article shows.
- Do not invent CLI flags, HTTP endpoints, or version requirements not in the source.
- When expanding prose, mark uncertainty by staying simpler — never by fabricating detail.
- Code tests must be consistent with the template and with article semantics.
- The tested function name must match the template (no hidden mandatory `solve`).
- Do not invent `"mock_session"` string inputs for object parameters — use `setup` stubs + `$call` / `run` tests.
- Quotes and identifiers from the article stay exact.
