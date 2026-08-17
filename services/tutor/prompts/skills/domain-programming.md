# Domain overlay: programming (technical family)

Use **only** when the sources are clearly about software, APIs, CLI, or code.
If the article is humanities, language, business, or science without software —
do not apply this overlay.

## Shape

One chapter = one idea in a real context from **this** article's stack.
Show a tiny working slice first (top-down), then name the parts.
Later chapters peel foundations and traps — they do not restart "what is
\<language\>" or advertise a product.

Do not invent a default language or framework. Identifiers, runtimes, and package
names come only from the sources (whatever they use).

## Theory

Friction or failure from the source world → one picture → worked snippet from the
source → name each API/command in prose → one trap. One analogy, then real names.

## Assess (if ON)

- Quizzes: apply/analyze (which call, which order, which side of a contrast) — not
  “what is \<product\>”.
- Practice: a **drill** — the same slice as the worked example, with a stub.
  Easy = fill the hole in the starter. Runtime matches the article (shell, Python,
  SQL, …). Not an olympiad spec and not a fake package.
- **CLI / Docker / DevOps sources:** learner pastes a Dockerfile, shell commands, or
  config (`kind: task` or `runtime: bash`) — never a Python/JS function that returns
  Dockerfile text as a string.

## Book

Chapters share one metaphor for the runtime of **this** stack. Chapter N opens on
the bug chapter N−1 just made possible. No “welcome to the language” after chapter 1.

## Anti-patterns

- Glossary-first chapter 1; product marketing as a lesson
- Practice that invents packages or APIs absent from the article
- Quizzes that only ask “what is \<product\>”
