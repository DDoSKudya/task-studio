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

/** Промежуточные стадии пайплайна → чип в прогресс-баре. */
export function mapCourseStageToUi(stage: string | null | undefined): CourseStageName | string {
  if (!stage) {
    return 'analyze'
  }
  if (stage === 'topic_bundle') {
    return 'theory'
  }
  if (stage === 'code_suitability') {
    return 'analyze'
  }
  return stage
}

export type CourseStageEvent = {
  type: 'stage' | 'done' | 'error' | 'consistency_gate' | 'code_suitability_gate' | 'ping'
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
  build_id?: string
}

export type StreamCourseResult =
  | { kind: 'done'; result: CourseFromArticleResponse }
  | { kind: 'consistency_gate'; event: CourseStageEvent }
  | { kind: 'code_suitability_gate'; event: CourseStageEvent }
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
  code_suitability_policy?: 'ask' | 'auto_open' | 'auto_skip'
  code_suitability_action?: 'keep_code' | 'open_tasks' | 'no_practice' | null
  course_depth?: 'light' | 'standard' | 'deep'
  practice_count?: number
  theory_count?: number | null
  build_id?: string | null
}

export type CourseBuildSummary = {
  build_id: string
  title: string
  status: 'running' | 'paused' | 'failed' | 'done'
  stage: string
  progress: number
  message: string
  chapter_total: number
  chapters_done: number
  error?: string | null
  created_at: string
  updated_at: string
  mode: string
}

export type CourseBuildDetail = CourseBuildSummary & {
  request: Record<string, unknown>
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
  if (event.type === 'consistency_gate' || event.type === 'code_suitability_gate') {
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
  if (state.gateEvent?.type === 'code_suitability_gate') {
    return { kind: 'code_suitability_gate', event: state.gateEvent }
  }
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
      if (event.type === 'ping') {
        continue
      }
      onEvent(event)
      applyCourseStageEvent(event, state)
    } catch {
      /* ignore */
    }
  }
  return rest
}
