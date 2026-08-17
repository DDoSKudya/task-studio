# harvest-adapt

## Status: canonical
## Applies to: all-providers
## Pack: author-full (preferred when article contains checks)

## Pipeline

Prefer adapting harvested article quizzes/homework into pack quizzes, then fill
gaps with claim-mcq.

## Gates

- Harvested items still pass claim-mcq style gates after adaptation
- Locale matches course request

## Forbidden

- Importing broken / empty harvested stems without repair

## Skills to compose

- `quiz-assessment-design`, `course-stage-json`

## Skills to skip

- none

## LLM brief

Adapt the harvested check into a fair MCQ for this chapter. Keep the tested idea;
fix wording and distractors. JSON only.
