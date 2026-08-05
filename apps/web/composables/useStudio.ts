import {
  consumeCourseSseBuffer,
  finalizeCourseStream,
  type CourseArticleVideo,
  type CourseBuildDetail,
  type CourseBuildSummary,
  type CourseFromArticleBody,
  type CourseFromArticleMeta,
  type CourseFromArticleResponse,
  type CourseStageEvent,
  type CourseStageName,
  type StreamCourseResult,
} from '~/utils/studio'

export type {
  CourseArticleVideo,
  CourseBuildDetail,
  CourseBuildSummary,
  CourseFromArticleMeta,
  CourseFromArticleResponse,
  CourseStageEvent,
  CourseStageName,
  StreamCourseResult,
}

export type CourseArticleInput = {
  title?: string | null
  content: string
  videos?: CourseArticleVideo[] | null
}

export type { CourseFromArticleBody }

export type FetchArticleFromUrlResponse = {
  title: string
  content: string
  source_url: string
  videos?: CourseArticleVideo[]
}

export type FetchArticleBatchItem = {
  url: string
  ok: boolean
  index: number
  title?: string | null
  content?: string | null
  source_url?: string | null
  videos?: CourseArticleVideo[]
  error?: string | null
}

export type FetchArticlesFromUrlsResponse = {
  results: FetchArticleBatchItem[]
  total: number
  ok_count: number
  error_count: number
}

export function useStudio() {
  const config = useRuntimeConfig()
  const { request } = useApi()

  async function fetchArticleFromUrl(url: string, options?: { signal?: AbortSignal }) {
    return request<FetchArticleFromUrlResponse>('/v1/studio/ai/fetch-article-from-url', {
      method: 'POST',
      body: { url },
      signal: options?.signal,
    })
  }

  async function fetchArticlesFromUrls(
    input: { urls?: string[]; text?: string },
    options?: { signal?: AbortSignal },
  ) {
    return request<FetchArticlesFromUrlsResponse>('/v1/studio/ai/fetch-articles-from-urls', {
      method: 'POST',
      body: {
        urls: input.urls ?? [],
        text: input.text ?? null,
      },
      signal: options?.signal,
    })
  }

  async function buildPack(
    manifest: Record<string, unknown>,
    assets: Array<{ path: string; content_base64: string }> = [],
  ) {
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

  async function streamCourseFromArticle(
    body: CourseFromArticleBody,
    onEvent: (event: CourseStageEvent) => void,
    options?: { signal?: AbortSignal },
  ): Promise<StreamCourseResult> {
    const response = await fetch(`${config.public.apiBase}/v1/studio/ai/course-from-article/stream`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(body),
      signal: options?.signal,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw createError({ statusCode: response.status, data: error })
    }

    const reader = response.body?.getReader()
    if (!reader) {
      return { kind: 'error', message: 'empty course stream' }
    }

    const onAbort = () => {
      void reader.cancel()
    }
    if (options?.signal) {
      if (options.signal.aborted) {
        await reader.cancel()
        return { kind: 'error', message: 'aborted' }
      }
      options.signal.addEventListener('abort', onAbort, { once: true })
    }

    const decoder = new TextDecoder()
    let buffer = ''
    const state = {
      doneResult: null as CourseFromArticleResponse | null,
      gateEvent: null as CourseStageEvent | null,
      streamError: null as string | null,
    }

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }
        buffer = consumeCourseSseBuffer(buffer + decoder.decode(value, { stream: true }), onEvent, state)
      }

      if (buffer.trim()) {
        consumeCourseSseBuffer(`${buffer}\n`, onEvent, state)
      }
    } catch (err) {
      if (options?.signal?.aborted || (err instanceof DOMException && err.name === 'AbortError')) {
        return { kind: 'error', message: 'aborted' }
      }
      throw err
    } finally {
      options?.signal?.removeEventListener('abort', onAbort)
    }

    if (options?.signal?.aborted) {
      return { kind: 'error', message: 'aborted' }
    }
    return finalizeCourseStream(state)
  }

  async function validateManifest(manifest: Record<string, unknown>) {
    return request<{ valid: boolean; errors: Array<{ path: string; message: string }> }>(
      '/v1/studio/validate',
      {
        method: 'POST',
        body: { manifest },
      },
    )
  }

  async function listCourseBuilds() {
    return request<CourseBuildSummary[]>('/v1/studio/ai/course-builds')
  }

  async function getCourseBuild(buildId: string) {
    return request<CourseBuildDetail>(`/v1/studio/ai/course-builds/${buildId}`)
  }

  async function discardCourseBuild(buildId: string) {
    await request(`/v1/studio/ai/course-builds/${buildId}`, { method: 'DELETE' })
  }

  return {
    buildPack,
    fetchArticleFromUrl,
    fetchArticlesFromUrls,
    streamCourseFromArticle,
    validateManifest,
    listCourseBuilds,
    getCourseBuild,
    discardCourseBuild,
  }
}
