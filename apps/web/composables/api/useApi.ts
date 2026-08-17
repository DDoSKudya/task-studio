import { readSetCookieHeaders, shouldRotateSession } from '~/utils/api'

export type ApiErrorBody = {
  detail?: string | Array<{ msg?: string }>
}

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
}

let sessionRotation: Promise<boolean> | null = null

export function useApi() {
  const config = useRuntimeConfig()

  function apiBase() {
    return import.meta.server ? config.apiBaseInternal : config.public.apiBase
  }

  async function forwardUpstreamCookies(event: ReturnType<typeof useRequestEvent>, headers: Headers) {
    if (!event) {
      return
    }
    const cookies = readSetCookieHeaders(headers)
    if (!cookies.length) {
      return
    }
    const { appendResponseHeader } = await import('h3')
    for (const cookie of cookies) {
      appendResponseHeader(event, 'set-cookie', cookie)
    }
  }

  function rotateSession(): Promise<boolean> {
    sessionRotation ??= $fetch(`${config.public.apiBase}/v1/auth/me`, {
      credentials: 'include',
    })
      .then(() => true)
      .catch(() => false)
      .finally(() => {
        sessionRotation = null
      })
    return sessionRotation
  }

  async function send<T>(path: string, init: RequestOptions, retried: boolean): Promise<T> {
    const { body, headers: initHeaders, ...rest } = init
    const headers = new Headers(initHeaders)
    const url = `${apiBase()}${path}`

    const payload: Record<string, unknown> = {
      ...rest,
      headers,
      credentials: 'include',
    }

    if (body !== undefined) {
      if (body instanceof FormData) {
        payload.body = body
      } else {
        if (!headers.has('Content-Type')) {
          headers.set('Content-Type', 'application/json')
        }
        payload.body = JSON.stringify(body)
      }
    }

    const method = String(rest.method ?? 'GET').toUpperCase()

    try {

      type JsonFetcher = (request: string, opts?: object) => Promise<T>
      let fetchJson: JsonFetcher
      if (import.meta.server) {

        // @ts-expect-error TS2321 excessive stack depth on Nuxt typed fetch
        fetchJson = useRequestFetch()
        const event = useRequestEvent()
        payload.onResponse = async ({ response }: { response: Response }) => {
          await forwardUpstreamCookies(event, response.headers)
        }
      } else {
        fetchJson = $fetch as unknown as JsonFetcher
      }
      const result = await fetchJson(url, {
        ...payload,
        ...(method === 'DELETE' ? { responseType: 'text' as const } : {}),
      })
      return (result ?? undefined) as T
    } catch (error) {
      const statusCode = typeof error === 'object' && error !== null && 'statusCode' in error
        ? Number((error as { statusCode: number }).statusCode)
        : 500
      const data = typeof error === 'object' && error !== null && 'data' in error
        ? (error as { data: ApiErrorBody }).data
        : undefined
      const rotatable = shouldRotateSession({
        path,
        statusCode,
        retried,
        onClient: Boolean(import.meta.client),
      })
      if (rotatable && (await rotateSession())) {
        return send<T>(path, init, true)
      }
      throw createError({ statusCode, data })
    }
  }

  async function request<T>(path: string, init: RequestOptions = {}): Promise<T> {
    return send<T>(path, init, false)
  }

  return { request, rotateSession }
}
