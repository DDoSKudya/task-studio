# Quality levels (L0–L3)

Every article→course build must declare the highest level it achieved.
**Without L0 the pack must not assemble.**

| Level | Meaning | Required evidence |
| --- | --- | --- |
| **L0 Structure** | TOC and phases are valid | Title gate OK; chapter/topic cap; `phase_order`; no missing step refs |
| **L1 Content** | Text teaches from the article | `key_claims` covered; no banned openers; no author-bio dumps in theory |
| **L2 Visual** | Chapter idea is visible | Source figure in study **or** mermaid/table from `visual_plan` |
| **L3 Assess** | Checks meaning | Claim-based MCQ; practice runtime from source; no letter-only choices (`A`/`B`/`C`/`D`) |

## Targets by pack

| Pack | Target |
| --- | --- |
| `preserve-7b` | Stable **L1**; **L2** when source has figures |
| `author-full` | **L2** and **L3** |
| `blocked` | No pack |

## Kill criteria (fail review)

- Topic title looks like a paragraph, markdown fragment (`![`, `***`), or author intro
- Theory is generic filler with no claim overlap to the source excerpt
- Quizzes are template/compiler stems (“according to this chapter…”, UI-only distractors) as the majority path
- Practice uses a fake package / wrong runtime while the article shows CLI/config
- Source images present in the article but **zero** figures in the manifest
