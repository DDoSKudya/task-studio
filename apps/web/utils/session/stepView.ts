import type { OutlineStep, OutlineTopic, PhaseProgress } from './types'
import { resolveAssetIdSrc, resolveMediaSrc } from '../media'

export type StepReveal = {
  passed: boolean
  gradable?: boolean
}

export function isLessonDone(
  lesson: OutlineStep,
  passedStepIds: ReadonlySet<string>,
  completedStepIds: ReadonlySet<string>,
): boolean {
  return passedStepIds.has(lesson.step_id) || completedStepIds.has(lesson.step_id)
}

export function moduleDoneCount(
  topic: OutlineTopic,
  passedStepIds: ReadonlySet<string>,
  completedStepIds: ReadonlySet<string>,
): number {
  return topic.steps.filter((lesson) => isLessonDone(lesson, passedStepIds, completedStepIds)).length
}

/** Фазы, которые реально есть в теме (study / practice / assess). */
export function phasesInTopic(topic: OutlineTopic): Set<OutlineStep['phase']> {
  return new Set(topic.steps.map((step) => step.phase))
}

function topicProgressRow(
  phaseProgress: readonly PhaseProgress[],
  topicId: string,
): PhaseProgress | undefined {
  return phaseProgress.find((row) => row.topic_id === topicId)
}

/**
 * Тема считается пройденной, когда закрыты все её фазы (не каждый шаг отдельно).
 * Опирается на phase_progress с бэкенда; без него — все шаги в completed/passed.
 */
export function isTopicComplete(
  topic: OutlineTopic,
  phaseProgress: readonly PhaseProgress[],
  passedStepIds: ReadonlySet<string>,
  completedStepIds: ReadonlySet<string>,
): boolean {
  if (!topic.steps.length) {
    return false
  }
  const row = topicProgressRow(phaseProgress, topic.topic_id)
  const phases = phasesInTopic(topic)
  if (row) {
    if (phases.has('study') && !(row.study_completed || row.study_skipped)) {
      return false
    }
    if (phases.has('practice') && !row.practice_completed) {
      return false
    }
    if (phases.has('assess') && !row.assess_completed) {
      return false
    }
    return true
  }
  return topic.steps.every((lesson) => isLessonDone(lesson, passedStepIds, completedStepIds))
}

export function outlineTopicsCompleted(
  outline: readonly OutlineTopic[],
  phaseProgress: readonly PhaseProgress[],
  passedStepIds: ReadonlySet<string>,
  completedStepIds: ReadonlySet<string>,
): number {
  return outline.filter((topic) =>
    isTopicComplete(topic, phaseProgress, passedStepIds, completedStepIds),
  ).length
}

export function isCurrentLesson(
  currentTopicId: string | null | undefined,
  currentStepId: string | null | undefined,
  topicId: string,
  stepId: string,
): boolean {
  return currentTopicId === topicId && currentStepId === stepId
}

export function stepNeedsPassToAdvance(
  requirePass: boolean,
  kind: string | null | undefined,
): boolean {
  if (!requirePass) {
    return false
  }
  return kind === 'quiz' || kind === 'code' || kind === 'task' || kind === 'lab'
}

export function isStepPassedLocally(input: {
  stepId: string | null | undefined
  kind: string | null | undefined
  passedStepIds: ReadonlySet<string>
  quizReveal: StepReveal | null
  codeReveal: StepReveal | null
  taskReveal: StepReveal | null
}): boolean {
  const { stepId, kind } = input
  if (!stepId) {
    return false
  }
  if (input.passedStepIds.has(stepId)) {
    return true
  }
  if (kind === 'quiz' && input.quizReveal?.passed) {
    return true
  }
  if (kind === 'code' && input.codeReveal?.passed) {
    return true
  }
  if (kind === 'task' && input.taskReveal?.passed) {
    return true
  }
  return false
}

export function canAdvanceToNext(input: {
  hasNext: boolean
  needsPass: boolean
  passed: boolean
}): boolean {
  if (!input.hasNext) {
    return false
  }
  if (!input.needsPass) {
    return true
  }
  return input.passed
}

export function taskRubricFromContent(content: Record<string, unknown> | null | undefined): string {
  if (!content) {
    return ''
  }
  const rubric = content.rubric
  return typeof rubric === 'string' ? rubric.trim() : ''
}

export function quizQuestionFromContent(content: Record<string, unknown> | null | undefined): string {
  if (!content) {
    return ''
  }
  const question = content.question
  return typeof question === 'string' ? question : ''
}

export function quizChoicesFromContent(content: Record<string, unknown> | null | undefined): string[] {
  if (!content) {
    return []
  }
  const choices = content.choices
  return Array.isArray(choices) ? choices.filter((item): item is string => typeof item === 'string') : []
}

export function hasRichStudyBody(content: Record<string, unknown> | null | undefined): boolean {
  if (!content) {
    return false
  }
  const body = content.body_html
  if (typeof body === 'string' && body.trim()) {
    return true
  }
  const images = content.images
  if (Array.isArray(images) && images.length) {
    return true
  }
  const examples = content.code_examples
  return Array.isArray(examples) && examples.length > 0
}

export function labInstructionsFromContent(
  content: Record<string, unknown> | null | undefined,
  richBody: boolean,
): string {
  if (richBody) {
    return ''
  }
  const instructions = content?.instructions
  return typeof instructions === 'string' ? instructions : ''
}

export function resolveStepVideoSrc(
  content: Record<string, unknown> | null | undefined,
  mediaBase: string,
): string {
  if (!content) {
    return ''
  }
  if (typeof content.asset_id === 'string') {
    const fromAsset = resolveAssetIdSrc(mediaBase, content.asset_id)
    if (fromAsset) {
      return fromAsset
    }
  }
  for (const key of ['video_url', 'url', 'src'] as const) {
    const value = content[key]
    if (typeof value === 'string') {
      const resolved = resolveMediaSrc(mediaBase, value)
      if (resolved) {
        return resolved
      }
    }
  }
  return ''
}

export function resolveStepVideoPoster(
  content: Record<string, unknown> | null | undefined,
  mediaBase: string,
): string {
  if (!content) {
    return ''
  }
  for (const key of ['poster', 'thumbnail', 'cover'] as const) {
    const value = content[key]
    if (typeof value === 'string') {
      const resolved = resolveMediaSrc(mediaBase, value)
      if (resolved) {
        return resolved
      }
    }
  }
  const first = Array.isArray(content.images) ? content.images.find((item) => typeof item === 'string') : null
  return typeof first === 'string' ? first : ''
}

const STEP_KIND_MARK_FALLBACK: Record<string, string> = {
  theory: 'T',
  video: 'V',
  quiz: 'Q',
  code: 'C',
  lab: 'L',
  task: 'A',
}

export function stepKindMark(
  kind: string,
  label: (key: string) => string,
  hasKey: (key: string) => boolean,
): string {
  const i18nKey = `session.kindMark.${kind}`
  if (hasKey(i18nKey)) {
    return label(i18nKey)
  }
  const fallback = STEP_KIND_MARK_FALLBACK[kind]
  if (fallback) {
    return fallback
  }
  return kind.slice(0, 1).toUpperCase()
}
