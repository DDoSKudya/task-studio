export type CourseArticleVideo = {
  url: string
  title?: string | null
}

export type CourseFromArticleMeta = {
  outcomes: string[]
  warnings: string[]
  chapters: string[]
  deviations?: Array<{ summary: string; sources: string[] }>
  article_count?: number
}

export type CourseFromArticleResponse = {
  manifest: Record<string, unknown>
  meta: CourseFromArticleMeta
}

export type CourseStageName =
  | 'consistency'
  | 'analyze'
  | 'theory'
  | 'polish'
  | 'quizzes'
  | 'code'
  | 'assemble'
  | 'done'
  | 'failed'

export type CourseStageEvent = {
  type: 'stage' | 'done' | 'error' | 'consistency_gate'
  stage?: CourseStageName | string
  status?: string
  progress?: number
  message?: string
  message_key?: string
  message_params?: Record<string, unknown>
  index?: number
  total?: number
  detail?: Record<string, unknown>
  manifest?: Record<string, unknown>
  meta?: CourseFromArticleMeta
  status_code?: number
}

export type StreamCourseResult =
  | { kind: 'done'; result: CourseFromArticleResponse }
  | { kind: 'consistency_gate'; event: CourseStageEvent }
  | { kind: 'error'; message: string }

export type CourseFromArticleBody = {
  article?: string | null
  articles?: Array<{
    title?: string | null
    content: string
    videos?: CourseArticleVideo[] | null
  }>
  title?: string | null
  locale?: string
  audience?: string | null
  runtime?: string
  runtime_version?: string
  quiz_count?: number
  code_count?: number
  ignore_deviations?: boolean
  include_theory?: boolean
  include_quizzes?: boolean
  include_code?: boolean
}

const EMPTY_META: CourseFromArticleMeta = {
  outcomes: [],
  warnings: [],
  chapters: [],
  deviations: [],
  article_count: 1,
}

export function applyCourseStageEvent(
  event: CourseStageEvent,
  state: {
    doneResult: CourseFromArticleResponse | null
    gateEvent: CourseStageEvent | null
    streamError: string | null
  },
): void {
  if (event.type === 'consistency_gate') {
    state.gateEvent = event
  }
  if (event.type === 'done' && event.manifest) {
    state.doneResult = {
      manifest: event.manifest,
      meta: event.meta ?? EMPTY_META,
    }
  }
  if (event.type === 'error') {
    state.streamError = event.message || 'course generation failed'
  }
}

export function finalizeCourseStream(state: {
  doneResult: CourseFromArticleResponse | null
  gateEvent: CourseStageEvent | null
  streamError: string | null
}): StreamCourseResult {
  if (state.gateEvent) {
    return { kind: 'consistency_gate', event: state.gateEvent }
  }
  if (state.streamError) {
    return { kind: 'error', message: state.streamError }
  }
  if (!state.doneResult) {
    return { kind: 'error', message: 'course stream ended without result' }
  }
  return { kind: 'done', result: state.doneResult }
}

export function consumeCourseSseBuffer(
  buffer: string,
  onEvent: (event: CourseStageEvent) => void,
  state: {
    doneResult: CourseFromArticleResponse | null
    gateEvent: CourseStageEvent | null
    streamError: string | null
  },
): string {
  const lines = buffer.split('\n')
  const rest = lines.pop() ?? ''
  for (const line of lines) {
    if (!line.startsWith('data:')) {
      continue
    }
    const payload = line.slice(5).trim()
    if (!payload) {
      continue
    }
    try {
      const event = JSON.parse(payload) as CourseStageEvent
      onEvent(event)
      applyCourseStageEvent(event, state)
    } catch {

    }
  }
  return rest
}
