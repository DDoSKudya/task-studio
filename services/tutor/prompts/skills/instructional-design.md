# Skill: instructional design (course quality)

Concrete authoring **invariants** — not academic labels in learner-facing output.

**Ownership:** chapter writing method (montage vs literary expand), figure policy,
and assess shape come from the **active strategy pack**. This skill does not override
strategy briefs. On preserve packs it may be omitted from compose entirely.

Genre craft lives in `domain-*.md`. Do not assume a coding stack, lab runtime, or
named LMS product. Match the sources.

## Quality invariants (every run)

1. **Chapter 1 = epitome** — simplest *complete* story / case / utterance a beginner
   could finish after that chapter alone. Forbidden: glossary dump, “what you will
   learn”, TOC photocopy.
2. **Later chapters elaborate** — one new condition, contrast, or voice on the same
   whole problem. Spiral reuse; no restart.
3. **Theory is self-sufficient** — calm running prose; assertion headings; no boxed
   pedagogy frames. Worked example stays in theory even if quizzes/practice are OFF.
4. **Assess only if ON** — quizzes *check* the objective (decision/contrast, not title
   recall). Practice *drills* the same chapter skill (ladder when several tasks).
5. **Parts flags are law** — never invent quizzes/homework in theory; never thin
   theory because later parts are OFF.

## Outcomes & objectives

Prefer measurable Bloom verbs — avoid "understand", "know", "learn about".

| Level | Example verbs (EN / RU) |
| --- | --- |
| Remember / Understand | define, describe / определить, описать |
| Apply | use, predict, implement / применить, предсказать |
| Analyze | compare, distinguish / сравнить, различить |
| Evaluate | justify, choose / обосновать, выбрать |

Template: **After this chapter the learner can \<verb\> \<skill\>.**
Course `outcomes` and every ON part (theory / quiz / practice) must evidence the
**same** chapter objective.

Address: **ты** (ru) or **you** (en) unless `book_spine.address` says otherwise —
one address for the whole book.

## Alignment checklist (silent, every stage)

- [ ] Title ↔ `learning_objective` ↔ theory (if ON) ↔ quiz (if ON) ↔ practice (if ON)
- [ ] `must_not_reteach` not re-defined (harder reuse OK)
- [ ] No homework / quiz / answer key inside theory
- [ ] Quizzes check the objective; practice repeats it

## Forbidden

- Essay stack (each chapter re-introduces the whole subject)
- Worksheet layout (pedagogy `##`, blockquote callouts, key-takeaway boxes)
- Generic filler (“важно понимать”, “рассмотрим основы”)
- Trivia quizzes or tasks that leave the chapter skill
- Unobservable outcomes (“понимать важность X”)

## When volume is capped

Same invariants, fewer chapters: **depth over breadth**. One solid drill beats three
invented stubs. Never inflate assess count to fill the UI.

Prose craft, density, and analogies → `expand-dense-prose` / montage briefs / domain
overlays — do not duplicate them here.
