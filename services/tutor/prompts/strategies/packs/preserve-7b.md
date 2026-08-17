# preserve-7b

## Status: manual-only (never auto-selected — see ADR D20)
## Applies to: all-providers
## When: explicitly requested source-fidelity run; model size alone never selects it

## Strategies

- curriculum: `curriculum/section-blueprint`
- theory: `theory/montage-preserve`
- quiz: `quiz/claim-mcq` (emergency: `quiz/theory-compiler` at most once per chapter)
- practice: `practice/harvest-then-drill`
- edit: `edit/gates-first`
- visual: `visual/source-figures-first` (+ `visual/mermaid-architecture` if no figure)

## Skills to compose

- `course-stage-json`, `anti-hallucination-source`, `pack-manifest-contract`
- `negative-constraints`, `quiz-assessment-design`, `practice-as-drill`
- `diagram-craft` only when `visual_plan` needs mermaid and no source figure
- domain overlay for the detected genre (programming / humanities / …)

## Skills to skip

- `expand-dense-prose` (conflicts with montage-preserve)
- `instructional-design` full rewrite cycle (conflicts with montage; use strategy briefs)
- `code-task-ladder` (preserve uses single harvest-then-drill, not a 3-rung ladder)
- `open-task-ladder` (same: one drill per topic, not a 3-rung open ladder)
- `book-polish` (no LLM polish stage on this pack; edit stays gates-first only)

## Effort notes

- Cap chapters and assess volume via policy (not by inventing new strategy IDs)
- `split_long_theory=false` for this pack
- `quiz_batch_size=1`; theory continues limited
- Genre-agnostic: same pack for any subject; domain overlay supplies medium-specific craft

## Target quality

L1 → L2 when source figures exist.

## LLM brief

You are building a course under pack preserve-7b for whatever genre the sources are.
Preserve article structure and assets. Do not rewrite chapters from scratch. Follow
section-blueprint titles, montage theory, claim-based quizzes, and include source
figures when present. Match the source medium (prose, code, argument, language drill)
— never invent a default tech stack.
