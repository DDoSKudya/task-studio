import type { CourseOutlineLesson, CourseOutlineModule, CoursePhase } from './outlineTypes'

export type { CourseOutlineLesson, CourseOutlineModule, CoursePhase } from './outlineTypes'

function phaseStepIds(topic: Record<string, unknown>, phase: CoursePhase): string[] {
  const phases = topic.phases
  if (phases && typeof phases === 'object' && !Array.isArray(phases)) {
    const body = (phases as Record<string, unknown>)[phase]
    if (body && typeof body === 'object' && !Array.isArray(body)) {
      const steps = (body as Record<string, unknown>).steps
      if (Array.isArray(steps)) {
        return steps.filter((item): item is string => typeof item === 'string')
      }
    }
  }
  const flat = topic[phase]
  if (Array.isArray(flat)) {
    return flat.filter((item): item is string => typeof item === 'string')
  }
  return []
}

function resolvePhaseOrder(
  manifest: Record<string, unknown> | null | undefined,
): CoursePhase[] {
  const defaults: CoursePhase[] = ['study', 'practice', 'assess']
  const policies = manifest?.policies
  if (!policies || typeof policies !== 'object' || Array.isArray(policies)) {
    return defaults
  }
  const raw = (policies as Record<string, unknown>).phase_order
  if (!Array.isArray(raw)) {
    return defaults
  }
  const ordered: CoursePhase[] = []
  const seen = new Set<string>()
  for (const item of raw) {
    if ((item === 'study' || item === 'practice' || item === 'assess') && !seen.has(item)) {
      ordered.push(item)
      seen.add(item)
    }
  }
  for (const phase of defaults) {
    if (!seen.has(phase)) {
      ordered.push(phase)
    }
  }
  return ordered
}

export function buildCourseOutline(
  manifest: Record<string, unknown> | null | undefined,
): CourseOutlineModule[] {
  const rawTopics = manifest?.topics
  const rawSteps = manifest?.steps
  if (!Array.isArray(rawTopics) || !rawSteps || typeof rawSteps !== 'object') {
    return []
  }
  const stepsMap = rawSteps as Record<string, unknown>
  const modules: CourseOutlineModule[] = []
  const phaseOrder = resolvePhaseOrder(manifest)

  rawTopics.forEach((item, topicOffset) => {
    if (!item || typeof item !== 'object') {
      return
    }
    const topic = item as Record<string, unknown>
    const topicIndex = topicOffset + 1
    const topicId = typeof topic.id === 'string' ? topic.id : `topic-${topicIndex}`
    const title = typeof topic.title === 'string' ? topic.title : topicId
    const lessons: CourseOutlineLesson[] = []
    let lessonIndex = 0
    for (const phase of phaseOrder) {
      for (const stepId of phaseStepIds(topic, phase)) {
        lessonIndex += 1
        const rawStep = stepsMap[stepId]
        const step = rawStep && typeof rawStep === 'object' ? (rawStep as Record<string, unknown>) : {}
        const stepTitle = typeof step.title === 'string' && step.title.trim() ? step.title : stepId
        const kind = typeof step.kind === 'string' ? step.kind : 'unknown'
        lessons.push({
          topicId,
          phase,
          stepId,
          title: stepTitle,
          kind,
          indexLabel: `${topicIndex}.${lessonIndex}`,
        })
      }
    }
    modules.push({ topicId, title, index: topicIndex, lessons })
  })

  return modules
}
