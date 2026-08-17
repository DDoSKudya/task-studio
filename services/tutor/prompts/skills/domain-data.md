# Domain overlay: data (analytics, SQL, tables, pipelines — technical family)

Use when the sources teach working with datasets, queries, or transforms.
If the article is pure software architecture without a dataset story, prefer
`domain-programming`. Do not invent schemas or columns.

## Shape

One running dataset and one question across the course when the sources allow it.
Later chapters query the same table — they do not invent a new toy dataset each time
unless the article does.

## Theory

Dataset → question → transform/query → how to read the result. Prefer tables and small
snippets from the source language (SQL, pandas, …). One analogy (warehouse, ledger),
then the real schema names.

## Assess (if ON)

- Quizzes: “which query/filter answers this question?”, not library trivia.
- Practice: one transform or query the chapter already showed. Starter may include the
  frame or schema. No unrelated ML or UI unless the source teaches it.

## Book

One running dataset/question across chapters when possible.

## Anti-patterns

- Invented schemas/columns; new toy dataset every chapter without source support
- Library trivia quizzes; unrelated ML/UI drills
- Practice that ignores the chapter’s query/transform
