export type StudioValidationIssue = {
  path: string
  message: string
}

export type StudioValidateResponse = {
  valid: boolean
  errors: StudioValidationIssue[]
}

export type StudioSuggestResponse = {
  suggestion: Record<string, unknown>
}

export type CourseFromArticleMeta = {
  outcomes: string[]
  warnings: string[]
  chapters: string[]
}

export type CourseFromArticleResponse = {
  manifest: Record<string, unknown>
  meta: CourseFromArticleMeta
}

export type CourseStageName = 'analyze' | 'theory' | 'quizzes' | 'code' | 'assemble' | 'done' | 'failed'

export type CourseStageEvent = {
  type: 'stage' | 'done' | 'error'
  stage?: CourseStageName | string
  status?: 'running' | 'done' | 'error' | string
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

export type CourseFromArticleBody = {
  article: string
  title?: string | null
  locale?: string
  audience?: string | null
  runtime?: string
  runtime_version?: string
  quiz_count?: number
  code_count?: number
}

export function useStudio() {
  const config = useRuntimeConfig()
  const { request } = useApi()

  async function validateManifest(manifest: Record<string, unknown>) {
    return request<StudioValidateResponse>('/v1/studio/validate', {
      method: 'POST',
      body: { manifest },
    })
  }

  async function buildPack(manifest: Record<string, unknown>, assets: Array<{ path: string; content_base64: string }>) {
    const response = await fetch(`${config.public.apiBase}/v1/studio/build`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ manifest, assets }),
    })
    if (!response.ok) {
      const error = (await response.json().catch(() => ({}))) as { detail?: string }
      throw createError({
        statusCode: response.status,
        data: error,
      })
    }
    return response.blob()
  }

  async function suggestFragment(body: {
    context: string
    step_kind: string
    prompt: string
    manifest_fragment?: Record<string, unknown>
  }) {
    return request<StudioSuggestResponse>('/v1/studio/ai/suggest', {
      method: 'POST',
      body,
    })
  }

  async function courseFromArticle(body: CourseFromArticleBody) {
    return request<CourseFromArticleResponse>('/v1/studio/ai/course-from-article', {
      method: 'POST',
      body,
    })
  }

  async function streamCourseFromArticle(
    body: CourseFromArticleBody,
    onEvent: (event: CourseStageEvent) => void,
  ): Promise<CourseFromArticleResponse> {
    const response = await fetch(`${config.public.apiBase}/v1/studio/ai/course-from-article/stream`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw createError({ statusCode: response.status, data: error })
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw createError({ statusCode: 502, message: 'empty course stream' })
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let result: CourseFromArticleResponse | null = null
    let streamError: string | null = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        break
      }
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''
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
          if (event.type === 'done' && event.manifest) {
            result = {
              manifest: event.manifest,
              meta: event.meta ?? { outcomes: [], warnings: [], chapters: [] },
            }
          }
          if (event.type === 'error') {
            streamError = event.message || 'course generation failed'
          }
        } catch {
          continue
        }
      }
    }

    if (streamError) {
      throw createError({ statusCode: 502, message: streamError })
    }
    if (!result) {
      throw createError({ statusCode: 502, message: 'course stream ended without result' })
    }
    return result
  }

  return {
    validateManifest,
    buildPack,
    suggestFragment,
    courseFromArticle,
    streamCourseFromArticle,
  }
}
