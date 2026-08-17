# Failure modes (article → course)

Cross-cutting catalog: known stupidity patterns for **local** models, **cloud APIs**,
and **IDE/agent** paths — and which layer owns the fix.

Genre-agnostic. Do not hardcode product stacks here; medium craft stays in `domain-*.md`.

## Layer ownership

| Layer | Owns |
| --- | --- |
| **Strategy pack** | What must be true (blueprint, montage vs expand, assess shape, gates) |
| **Provider profile** | How this runtime talks (language mix, length, token thrift) |
| **Code gates / policy** | Enforce after the model (titles, letter choices, JSON parse, pack pick) |
| **Skill / role** | How to write — never overrides an active strategy |

Conflict rule: pack + gates win. Provider tone cannot change strategy IDs.

## Local / small open models (Ollama, ~7B)

Observed / expected failure modes and mitigations:

| Failure | Symptom | Owner |
| --- | --- | --- |
| Literary rewrite from scratch | Thin filler, dropped claims/figures | Pack `preserve-7b` → `theory/montage-preserve`; skip `expand-dense-prose` |
| Sliding-window / first-sentence TOC | Garbage chapter titles | `curriculum/section-blueprint` + title sanitize gates |
| Letter-only MCQ choices | `["A","B","C","D"]` or `A)` prefixes | `quiz/claim-mcq` + choice gates + quiz repair |
| Meta / title-paraphrase stems | “main goal of this chapter” | claim-mcq gates + quiz skill |
| Invented stack / packages | Wrong runtime, fake deps | harvest-then-drill + anti-hallucination + practice runtime detect |
| JSON fences / preamble | ```json around stage output | `course-stage-json` + json_mode retries |
| Truncation mid-object | Half JSON at token cap | Small schemas, batch=1, continue limits, validate+retry |
| Language mix / wrong script | RU+EN mash, unexpected scripts | `provider/ollama-quality` (+ polish pass) |
| Worksheet pedagogy boxes | Введение / Ловушка headings | negative-constraints + montage brief |
| Over-assess to “fill UI” | Many empty quizzes/tasks | Volume caps in policy; parts flags are law |
| Tiny model (&lt; min) | Unusable course body | Pack `blocked` — do not assemble |
| Encyclopedia HTTP 403 | Wikipedia/simplewiki block bare browser GET | `page_fetch` → Wikimedia REST HTML for `/wiki/…` |

Industry pattern we already mirror: **step-wise model selection** — judgment-heavy
work (blueprint, expand) needs more capacity; preserve packs keep structure deterministic
and text short ([hybrid routing notes](https://notes.muthu.co/2026/07/local-first-llm-routing-use-small-models-for-easy-questions-and-cloud-models-for-hard-ones/),
[Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)).

## Cloud / strong API (external)

| Failure | Symptom | Owner |
| --- | --- | --- |
| Over-rewrite / LMS cosplay | Generic LMS callouts, forced coding micro-lessons | Role + instructional-design genre rule + domain overlay |
| Long-context drift | Later chapters ignore blueprint / earlier claims | Per-chapter context; section-blueprint as law; quality gate patches |
| Invented facts / citations | APIs, dates, quotes not in sources | anti-hallucination-source + gates |
| Quiz trivia / title recall | Stems ignore objectives | claim-mcq / harvest-adapt + quiz skill |
| Practice olympiad novelty | Tasks leave the chapter skill | ladder-3 + practice-as-drill |
| Ignoring parts OFF | Quizzes/homework inside theory | Author parts block + negative-constraints |

Prefer **author-full** pack (literary-expand + ladder + polish). Still pass L0 title /
figure / choice gates — strength does not waive structure.

## IDE / cloud agent path (Cursor via cursor-proxy)

Agent-specific risks (scope creep, specification drift, confident wrong rewrites) are
documented in the wild for coding agents; for **course JSON** the same patterns show up as:

| Failure | Symptom | Owner |
| --- | --- | --- |
| Drive-by rewrite of source meaning | Course replaces article substance | anti-hallucination + montage/expand briefs; gates on claims |
| Specification drift across stages | Outline vs theory vs quiz disagree | Blueprint artifact + chapter quality gate + alignment checklist |
| Markdown-fenced / chatty JSON | Stage payload not bare JSON | course-stage-json + parse/normalize in code |
| Over-scaffolding a stack | Default language/framework not in sources | Genre rule in role/strategies; domain overlay only |
| Silent soft-fail | Empty assess accepted as OK | Prefer hard validate+retry over fail-soft on course builds |

Harness policy: Cursor/external → `author-full` (see `provider_policy.py`). Provider
tone file remains `provider/external` unless a dedicated Cursor profile is added.

## What we intentionally do **not** put in strategies

- Hybrid **router** that switches cloud↔local mid-chapter (ops/policy concern; not MD law)
- Multi-agent LangGraph course factories (orchestration is our pipeline code)
- Self-consistency N-draft loops on Ollama (too expensive; critique→patch instead)
- Product names as required curriculum content

## Maintenance

When a new failure appears in a real course build:

1. Classify: structure / assess / transport / genre.
2. Prefer a **gate in code** if the model keeps lying.
3. Prefer a **strategy** change if the product law was wrong.
4. Prefer a **provider** line if only one runtime talks that way.
5. Update this table with the owner — do not duplicate kill-lists into messages.
