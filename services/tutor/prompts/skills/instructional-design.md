# Skill: instructional design (course quality)

Translate proven ID practice into **concrete authoring rules** — not academic labels in output.

Sources this skill encodes: Merrill's First Principles, backward design (outcomes →
evidence → activities), Bloom's revised taxonomy, cognitive-load chunking, worked
examples before practice.

## Course arc (one problem, one book)

1. **Problem-centered** — the course solves one real learner problem
   (e.g. "understand when flush runs vs commit"), not a TOC photocopy.
2. **Activation → demonstration → application → integration** — each chapter
   micro-cycle:
   - hook from prior knowledge or a failure the reader already met;
   - show (worked example / diagram);
   - name the idea;
   - one trap or contrast;
   - bridge to the next chapter (no full re-cap of the course).
3. **Backward design** — course `outcomes` are observable; every chapter has a
   **`learning_objective`** (one Bloom verb + one skill). Theory, quiz, and practice
   for that chapter must evidence **the same objective** — not random trivia.

## Bloom verbs (use in objectives & outcomes)

Prefer measurable verbs — avoid "understand", "know", "learn about".

| Level | Use when | Example verbs (EN / RU) |
| --- | --- | --- |
| Remember / Understand | foundations only | define, describe / определить, описать |
| Apply | most code courses | implement, use, predict / применить, предсказать |
| Analyze | contrasts, debugging | compare, distinguish, explain why / сравнить, различить |
| Evaluate | trade-offs | justify, choose / обосновать, выбрать |

Chapter objective template: **After this chapter the learner can \<verb\> \<skill\>.**

## Cognitive load (anti-bloat)

- **One primary idea per chapter** — if the title needs "and", split or pick one focus.
- **7±2 chunks** inside a chapter: ≤6 `##` sections; each section = one move.
- **Signal > noise:** every paragraph must advance the chapter objective or the worked
  example. Delete throat-clearing, course-wide intros, and re-definitions of prior chapters.
- **Density budget:** ~400–900 words of teaching prose per chapter (excluding code fences).
  Shorter is fine when the source is thin; never pad to hit word count.
- **Progressive complexity:** example-first for novices; name jargon only after the picture.

## Worked examples & practice ladder

- Theory: **one** complete worked example per chapter (≤40 lines code); second example
  only if it teaches a distinct sub-skill.
- Quiz: tests the chapter objective at **Apply** or **Analyze** — not recall of dates/names.
- Code ladder: easy = one idea from the chapter; medium = combine 2–3; hard = realistic
  constraint. Difficulty must **fade** scaffolding (less hint in template at hard level).

## Alignment checklist (every stage)

Before emitting JSON, silently verify:

- [ ] Chapter title ↔ `learning_objective` ↔ theory content ↔ quiz stem ↔ code brief
      describe the **same skill**.
- [ ] `must_not_reteach` topics are absent from this chapter's body.
- [ ] No homework/quiz/answer-key material inside theory.
- [ ] Assess/practice do not re-teach — they **check** what theory already showed.

## Forbidden quality failures

- Essay stack: each chapter re-introduces the whole subject.
- Generic filler that could fit any course ("важно понимать", "рассмотрим основы").
- Trivia quizzes disconnected from chapter objectives.
- Three code tasks that differ only by variable names.
- Outcomes that cannot be observed ("понимать важность X").
