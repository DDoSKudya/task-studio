# Editor grammars

Custom Monarch grammars for languages that Monaco does not ship with built-in support.

## Layout

```
editor_grammars/
  example.json
  <language>.json
```

Each file:

```json
{
  "language": "example",
  "monarch": { "tokenizer": { "root": [] } }
}
```

`editor-core` loads `editor_grammars/<language>.json` at runtime and registers the Monarch provider.

## When to add a grammar

- The pack uses a runtime without a built-in Monaco language id.
- LSP is optional or unavailable for that language.
- Syntax highlighting is still required (`editor_mode: syntax_only` or no LSP container).

## Template

Copy `example.json` and replace `language` plus tokenizer rules.
