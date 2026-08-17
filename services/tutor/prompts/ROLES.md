# Task Studio LLM prompt map

Prompts are modular **roles + skills + strategies + provider profiles** inside a small
**harness** (model + context builder + workflow stages + verifiers). Framing draws on:

- [Model vs effort](https://habr.com/ru/articles/1057268/)
- [Harness / meta-harness](https://habr.com/ru/companies/postgrespro/articles/1045532/)
- [Prompt structure & CoT](https://habr.com/ru/articles/827546/)
- [AUTOMAT / output contracts](https://habr.com/ru/companies/lanit/articles/812261/)
- [Auto-prompting (CoolPrompt) — future, not in-repo yet](https://habr.com/ru/articles/957694/)

| Lever | Meaning here |
| --- | --- |
| **Model** φ | Ollama / external / Cursor — capability ceiling |
| **Harness** θ | Prompts, skills, strategies, budgets, polish/retry stages, delimiters |
| **Effort** | How hard the harness tries (context size, polish, retries) |
| **Skills** | Discrete patches — prefer patching skills over rewriting core |
| **Strategies** | Product law for article→course (gates, forks, packs) — provider-agnostic |
| **Provider** | How this runtime talks (Ollama thrift vs strong API) — see also `strategies/failure-modes.md` |

Rule of thumb: fix context/skills first; raise effort for weak models; change model when it confidently fails despite good context.  
Full prompt replacement is destructive — evolve skills as patches ([harness article](https://habr.com/ru/companies/postgrespro/articles/1045532/)).  
Course strategies live under `prompts/strategies/` and **override skills on conflict**
(see `strategies/README.md`). Packs (`preserve-7b`, `author-full`, `blocked`) apply to
every provider; only effort knobs change. Map local/cloud/agent failure modes to owners
in `strategies/failure-modes.md` — do not duplicate kill-lists into stage messages.

## Harness stages (tutor chat)

| Stage | What happens |
| --- | --- |
| 1. Context build | Role + skills + provider + outline/page in XML delimiters (`<course_outline>`, `<current_page>`) |
| 2. Draft | Single completion (buffered on Ollama; streamed on external) |
| 3. Polish (Ollama) | Second pass: language/script cleanup |
| 4. Quality gate | Unexpected scripts / language mismatch → one more polish |
| 5. Emit | One SSE token (Ollama) or stream (external) |

Hints / Pack Studio skip polish; Pack Studio is JSON-only (strict output contract).  
**Grade / article / course stages** use format forcing + one JSON **repair-pass** when parse fails.  
**Article → course** uses a hybrid schedule for speed without breaking book unity:
analyze (+ `book_spine`) sequential → theory chapters 1–2 serial → mid chapters
parallel on external APIs only (Ollama stays serial) → light **book polish**
→ quizzes∥code parallel on external.
Multi-item stages (quizzes, code/tasks, polish, analyze chapter details)
emit **one item per LLM call** to avoid truncated JSON.
Multi-article starts at analyze (no consistency gate).

## Layout

```
prompts/
  shared/          core + chat context
  roles/           study_chat, practice_chat, contextual_hints, pack_studio, grade_check, course_from_article
  skills/          socratic, atypical-cases, negative-constraints, expand-dense-prose, diagram-craft, …
  strategies/      packs + curriculum/theory/quiz/practice/edit/visual (English MD; all providers)
  provider/        ollama-quality, ollama-polish, external
```

Composer: `app.domain.prompts.build_system_prompt(PromptRequest)`.  
Strategies: `app.domain.course_strategies` (`load_strategy`, `resolve_strategy_pack`).  
Learner turn wrapper: `format_learner_turn` (`<learner_message>` + `<response_contract>`).

## AI contours (product — do not mix)

Isolated harness invocations, **not** shared chat transcripts:

| Contour | Domain package | `LlmTaskKind` | History | Notes |
| --- | --- | --- | --- | --- |
| **A** URL → article | `fetch_article_from_url` | `chat` (dechrome; rescue if thin) | no | Direct/reader MD → optional LLM rescue if &lt;80 chars → LLM marks ads → local delete |
| **B** Article → course | `course_from_article` | `course_topic_bundle` | no | Staged JSON; own corpus clip |
| **C** Grade fallback | `grade` | `grade` → chat model lane | no | After Stepik/Piston/local fail |
| **D** Learner chat / hints | `chat` | `chat` / `hints` | client history only | Coaching; never grades |

Shared transport: `app.domain.llm` + user provider settings.  
Shared **policy** routing: `OLLAMA_MODEL_CHAT` vs `OLLAMA_MODEL_COURSE` (`OLLAMA_TASK_ROUTING`).  
Do **not** share conversation_id / history across B↔C↔D. Do **not** reintroduce LLM into A.

## Role × skills × provider

| Mode | Role | Always | Conditional | Provider |
| --- | --- | --- | --- | --- |
| Chat / study | `study_chat` | `socratic`, `atypical-cases`, `negative-constraints`, `kind-*`, `ground-on-page` | `sql-coach`; `token-budget` if Ollama | ollama-quality / external |
| Chat / practice | `practice_chat` | + `attempt-review`, `verify-with-checks`, `ground-on-page` | + `light-cot` if external; sql/token-budget | same |
| Hints | `contextual_hints` | `socratic`, `atypical-cases`, `negative-constraints`, `kind-*` | `few-shot-hints` (external) / `few-shot-hints-compact` (Ollama); sql/token-budget | same |
| Grade check | `grade_check` | `grade-json-contract`, `grade-duty`, `grade-evidence`, `negative-constraints`, `grade-quiz`/`grade-code`/`grade-task`/`grade-lab` | `sql-coach` + `token-budget` if needed | ollama-quality / external |
| Pack Studio | `pack_studio` | (JSON contract + shape example in role) | — | — |
| Article URL → MD | `article_from_url` | `url-to-markdown`, `article-dechrome`, `anti-hallucination-source`, `negative-constraints` | `token-budget` if Ollama | ollama-quality / external |
| Article → course | `course_from_article` | Skills from active **strategy pack** (`preserve-7b` / `author-full`); always include stage JSON + anti-hallucination + pack contract + negative-constraints | stage skills filtered by pack (`expand-dense-prose` only on `author-full`); `token-budget` if Ollama; video/figures from sources | ollama-quality / external |

## Context budgets

| Profile | Outline | Page | Starter | History |
| --- | --- | --- | --- | --- |
| Compact (Ollama) | 24 | 1200 | 400 | 6 |
| Full (external) | 80 | 3500 | 900 | 24 |

Ollama calls also set `num_ctx=4096` and `max_tokens` caps so CPU KV-cache does not explode.

## Ollama ops (Docker only)

Runtime: Compose service `ollama` on network `internal`. Tutor uses `OLLAMA_URL=http://ollama:11434`.  
Models live in volume `data/ollama`. Host-installed Ollama / llama.cpp are **out of band** for this project.

Sources: [squeeze local LLMs](https://habr.com/ru/articles/1025132/), [weak hardware tiers](https://habr.com/ru/companies/paybeam/articles/1027242/), [Arch speed notes](https://habr.com/ru/articles/1045898/), [local RAG + Ollama](https://habr.com/ru/companies/first/articles/1062546/).

| Topic | Takeaway for Task Studio |
| --- | --- |
| Model choice | Course: **qwen2.5:7b on GPU**, **qwen2.5:3b on CPU** (`hardware.py`). Both build the full course; 3B uses more, smaller requests |
| Below minimum | 1.5B and smaller are for chat/hints only — course build refuses them |
| Context size | Huge `num_ctx` kills CPU t/s inside the container — compact budgets + `num_ctx=4096` |
| Host tools | Do not assume `ollama` on the host PATH; always `compose … exec ollama …` |
| Quantization | Library tags via `ollama pull` are enough for PET |
| RAG | Course digest + page text only; no separate embedding container yet |
| Keep-alive | `OLLAMA_KEEP_ALIVE=30m` so draft+polish reuse a warm model in-container |

```bash
docker compose -f deploy/docker-compose.yml --env-file .env --profile full exec ollama ollama pull qwen2.5:7b
# CPU profile:
docker compose -f deploy/docker-compose.yml --env-file .env --profile full exec ollama ollama pull qwen2.5:3b
```

## Intentionally not in v1

- Genetic / CoolPrompt auto-optimization loops
- Self-consistency (N independent drafts) — too expensive on Ollama; use per-chapter critique→patch instead (`chapter-quality-gate`, `theory_quality_rounds=2`)
- RAG over pack corpus beyond course digest
- Tool-calling tutor agent
- LLM override of a **successful** Stepik/Piston/local harness result (fallback only)

## Authoring rules

- System prompts in English; learner-facing language at runtime.
- AUTOMAT-style: role, audience, action, output, atypical cases, topic whitelist — keep each skill short.
- Prefer skill patches over rewriting `shared/core`.
- Placeholders: `{{step_kind}}`, `{{step_title}}`, `{{language_name}}` (polish).
- Clear `##` / `###` separators in assembled context ([prompt structure](https://habr.com/ru/companies/lanit/articles/812261/)).
