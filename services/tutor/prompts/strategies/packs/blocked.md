# blocked

## Status: canonical
## Applies to: all-providers
## When: model below course minimum (e.g. below qwen2.5:3b)

## Strategies

- none — do not assemble a pack

## Skills to compose

- none

## Skills to skip

- pack id `blocked` clears every course_from_article skill in compose (see `filter_skills_for_pack`)
- listed for humans: `course-stage-json`, `anti-hallucination-source`, `pack-manifest-contract`,
  `negative-constraints`, `instructional-design`, `curriculum-synthesis`, `expand-dense-prose`,
  `diagram-craft`, `book-polish`, `quiz-assessment-design`, `code-task-ladder`, `open-task-ladder`,
  `practice-as-drill`, `chapter-quality-gate`

## Pipeline

Refuse the build with a clear warning. Suggest pulling a capable course model.

## LLM brief

(empty — no course generation)
